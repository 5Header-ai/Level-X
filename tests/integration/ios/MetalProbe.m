/* SPDX-License-Identifier: MIT */
#import <UIKit/UIKit.h>
#import <Metal/Metal.h>
#import <dispatch/dispatch.h>
#include <stdint.h>
#include <string.h>
#include <sys/sysctl.h>
#include <sys/utsname.h>

static NSString *BuildVersion(void)
{
    char build[128] = {0};
    size_t size = sizeof(build);
    if (sysctlbyname("kern.osversion", build, &size, NULL, 0) != 0) return @"unknown";
    return [NSString stringWithUTF8String:build] ?: @"unknown";
}

static NSString *Complete(id<MTLCommandBuffer> command)
{
    if (!command) return @"command buffer unavailable";
    dispatch_semaphore_t done = dispatch_semaphore_create(0);
    [command addCompletedHandler:^(id<MTLCommandBuffer> cb) {
        dispatch_semaphore_signal(done);
    }];
    [command commit];
    if (dispatch_semaphore_wait(done, dispatch_time(DISPATCH_TIME_NOW, 10 * NSEC_PER_SEC))) {
        return @"TIMEOUT: GPU work cannot be cancelled; restart app before another run";
    }
    if (command.status != MTLCommandBufferStatusCompleted) {
        return command.error.localizedDescription ?: @"command did not complete successfully";
    }
    return nil;
}

static NSDictionary *Probe(void)
{
    struct utsname machine = {0};
    NSString *machineName = uname(&machine) == 0
        ? [NSString stringWithUTF8String:machine.machine] : @"unknown";
    NSMutableDictionary *r = [@{
        @"schema_version": @1, @"probe_version": @"0.1.0",
        @"status": @"FAIL", @"compute": @"NOT RUN", @"render_clear": @"NOT RUN",
        @"os": UIDevice.currentDevice.systemVersion, @"build": BuildVersion(),
        @"machine": machineName ?: @"unknown",
        @"timestamp": @([NSDate date].timeIntervalSince1970)
    } mutableCopy];
    id<MTLDevice> device = MTLCreateSystemDefaultDevice();
    r[@"metal_device_available"] = @(device != nil);
    if (!device) { r[@"error"] = @"MTLCreateSystemDefaultDevice returned nil"; return r; }
    r[@"device_name"] = device.name ?: @"unknown";
    r[@"apple6_reported"] = @([device supportsFamily:MTLGPUFamilyApple6]);
    id<MTLCommandQueue> queue = [device newCommandQueue];
    if (!queue) { r[@"error"] = @"newCommandQueue failed"; return r; }

    NSError *error = nil;
    NSString *source = @"#include <metal_stdlib>\nusing namespace metal;\n"
        @"kernel void probe(device uint *out [[buffer(0)]], uint i [[thread_position_in_grid]]) {"
        @" if (i < 256) out[i] = (i * 1664525u + 1013904223u) ^ 0x5a5a5a5au; }";
    id<MTLLibrary> lib = [device newLibraryWithSource:source options:nil error:&error];
    id<MTLFunction> fn = [lib newFunctionWithName:@"probe"];
    if (!lib || !fn) { r[@"error"] = error.localizedDescription ?: @"shader unavailable"; return r; }
    id<MTLComputePipelineState> pipeline = [device newComputePipelineStateWithFunction:fn error:&error];
    if (!pipeline) { r[@"error"] = error.localizedDescription ?: @"compute pipeline unavailable"; return r; }
    id<MTLBuffer> out = [device newBufferWithLength:256 * sizeof(uint32_t)
                                          options:MTLResourceStorageModeShared];
    if (!out || !out.contents) { r[@"error"] = @"shared compute buffer unavailable"; return r; }
    memset(out.contents, 0xCD, out.length);
    id<MTLCommandBuffer> compute = [queue commandBuffer];
    id<MTLComputeCommandEncoder> encoder = [compute computeCommandEncoder];
    if (!encoder) { r[@"error"] = @"compute encoder unavailable"; return r; }
    [encoder setComputePipelineState:pipeline];
    [encoder setBuffer:out offset:0 atIndex:0];
    NSUInteger threads = MIN((NSUInteger)64, pipeline.maxTotalThreadsPerThreadgroup);
    if (!threads) { [encoder endEncoding]; r[@"error"] = @"zero threadgroup limit"; return r; }
    [encoder dispatchThreadgroups:MTLSizeMake((256 + threads - 1) / threads, 1, 1)
            threadsPerThreadgroup:MTLSizeMake(threads, 1, 1)];
    [encoder endEncoding];
    NSString *failure = Complete(compute);
    if (failure) { r[@"error"] = failure; r[@"compute"] = @"FAIL"; return r; }
    const uint32_t *values = out.contents;
    for (uint32_t i = 0; i < 256; ++i) {
        uint32_t expected = (i * 1664525u + 1013904223u) ^ 0x5a5a5a5au;
        if (values[i] != expected) {
            r[@"error"] = [NSString stringWithFormat:@"compute mismatch at %u: %u != %u", i, values[i], expected];
            r[@"compute"] = @"FAIL"; return r;
        }
    }
    r[@"compute"] = @"PASS";

    MTLTextureDescriptor *desc = [MTLTextureDescriptor
        texture2DDescriptorWithPixelFormat:MTLPixelFormatRGBA8Unorm width:8 height:8 mipmapped:NO];
    desc.usage = MTLTextureUsageRenderTarget;
    desc.storageMode = MTLStorageModePrivate;
    id<MTLTexture> texture = [device newTextureWithDescriptor:desc];
    id<MTLBuffer> pixels = [device newBufferWithLength:256 * 8 options:MTLResourceStorageModeShared];
    if (!texture || !pixels || !pixels.contents) { r[@"error"] = @"render resources unavailable"; return r; }
    memset(pixels.contents, 0xCD, pixels.length);
    MTLRenderPassDescriptor *pass = [MTLRenderPassDescriptor renderPassDescriptor];
    pass.colorAttachments[0].texture = texture;
    pass.colorAttachments[0].loadAction = MTLLoadActionClear;
    pass.colorAttachments[0].storeAction = MTLStoreActionStore;
    pass.colorAttachments[0].clearColor = MTLClearColorMake(1, 0, 1, 1);
    id<MTLCommandBuffer> render = [queue commandBuffer];
    id<MTLRenderCommandEncoder> renderer = [render renderCommandEncoderWithDescriptor:pass];
    if (!renderer) { r[@"error"] = @"render encoder unavailable"; return r; }
    [renderer endEncoding];
    id<MTLBlitCommandEncoder> blit = [render blitCommandEncoder];
    if (!blit) { r[@"error"] = @"blit encoder unavailable"; return r; }
    [blit copyFromTexture:texture sourceSlice:0 sourceLevel:0 sourceOrigin:MTLOriginMake(0,0,0)
              sourceSize:MTLSizeMake(8,8,1) toBuffer:pixels destinationOffset:0
      destinationBytesPerRow:256 destinationBytesPerImage:256*8];
    [blit endEncoding];
    failure = Complete(render);
    if (failure) { r[@"error"] = failure; r[@"render_clear"] = @"FAIL"; return r; }
    const uint8_t *bytes = pixels.contents;
    for (NSUInteger y = 0; y < 8; ++y) for (NSUInteger x = 0; x < 8; ++x) {
        const uint8_t *p = bytes + y*256 + x*4;
        if (p[0] != 255 || p[1] != 0 || p[2] != 255 || p[3] != 255) {
            r[@"error"] = @"render readback mismatch"; r[@"render_clear"] = @"FAIL"; return r;
        }
    }
    r[@"render_clear"] = @"PASS";
    r[@"status"] = @"PASS";
    return r;
}

@interface ProbeController : UIViewController
@property(nonatomic, strong) UITextView *text;
@end
@implementation ProbeController
- (void)viewDidLoad
{
    [super viewDidLoad];
    self.text = [[UITextView alloc] initWithFrame:self.view.bounds];
    self.text.autoresizingMask = UIViewAutoresizingFlexibleWidth | UIViewAutoresizingFlexibleHeight;
    self.text.editable = NO;
    self.text.font = [UIFont monospacedSystemFontOfSize:13 weight:UIFontWeightRegular];
    self.text.text = @"Level X Metal Probe\nRunning compute and render readback…";
    [self.view addSubview:self.text];
    dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED, 0), ^{
        @autoreleasepool {
            NSDictionary *result = Probe();
            NSData *json = [NSJSONSerialization dataWithJSONObject:result options:NSJSONWritingPrettyPrinted error:NULL];
            NSURL *documents = [NSFileManager.defaultManager URLsForDirectory:NSDocumentDirectory inDomains:NSUserDomainMask].firstObject;
            NSURL *url = [documents URLByAppendingPathComponent:@"metal-probe.json"];
            NSError *saveError = nil;
            BOOL saved = [json writeToURL:url options:NSDataWritingAtomic error:&saveError];
            NSString *text = [[NSString alloc] initWithData:json encoding:NSUTF8StringEncoding];
            NSLog(@"LEVELX_METAL_PROBE %@", text);
            dispatch_async(dispatch_get_main_queue(), ^{
                self.text.text = saved ? text : [text stringByAppendingFormat:@"\nSave failed: %@", saveError];
            });
        }
    });
}
@end

@interface AppDelegate : UIResponder <UIApplicationDelegate>
@property(nonatomic, strong) UIWindow *window;
@end
@implementation AppDelegate
- (BOOL)application:(UIApplication *)application didFinishLaunchingWithOptions:(NSDictionary *)options
{
    self.window = [[UIWindow alloc] initWithFrame:UIScreen.mainScreen.bounds];
    self.window.rootViewController = [ProbeController new];
    [self.window makeKeyAndVisible];
    return YES;
}
@end

int main(int argc, char *argv[])
{
    @autoreleasepool { return UIApplicationMain(argc, argv, nil, NSStringFromClass(AppDelegate.class)); }
}
