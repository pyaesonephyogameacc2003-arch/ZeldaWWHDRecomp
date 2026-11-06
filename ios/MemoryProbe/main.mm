#import <UIKit/UIKit.h>
#import <mach/mach.h>
#import <mach/mach_vm.h>
#import <signal.h>
#import <sys/mman.h>
#import <unistd.h>

static uint8_t *gGuestBase = nullptr;
static size_t gPageSize = 0;
static volatile sig_atomic_t gWriteFaultHandled = 0;

static void probeSignalHandler(int signalNumber, siginfo_t *info, void *) {
    uintptr_t address = reinterpret_cast<uintptr_t>(info ? info->si_addr : nullptr);
    uintptr_t watched = reinterpret_cast<uintptr_t>(gGuestBase) + (gPageSize * 2);
    if (gGuestBase && address >= watched && address < watched + gPageSize &&
        (signalNumber == SIGBUS || signalNumber == SIGSEGV) &&
        mprotect(reinterpret_cast<void *>(watched), gPageSize, PROT_READ | PROT_WRITE) == 0) {
        gWriteFaultHandled = 1;
        return;
    }

    // This probe only handles its own watched-page fault. Any unrelated fault
    // is restored to the default disposition and re-raised.
    signal(signalNumber, SIG_DFL);
    raise(signalNumber);
}

@interface ProbeAppDelegate : UIResponder <UIApplicationDelegate>
@property(nonatomic, strong) UIWindow *window;
@end

@implementation ProbeAppDelegate
- (BOOL)application:(UIApplication *)application didFinishLaunchingWithOptions:(NSDictionary *)options {
    (void)application;
    (void)options;
    self.window = [[UIWindow alloc] initWithFrame:UIScreen.mainScreen.bounds];
    UIViewController *controller = [UIViewController new];
    controller.view.backgroundColor = UIColor.systemBackgroundColor;
    UILabel *label = [[UILabel alloc] initWithFrame:CGRectInset(controller.view.bounds, 20, 20)];
    label.autoresizingMask = UIViewAutoresizingFlexibleWidth | UIViewAutoresizingFlexibleHeight;
    label.numberOfLines = 0;
    label.textAlignment = NSTextAlignmentCenter;
    label.text = @"Wind Waker HD\niOS memory compatibility probe…";
    controller.view = controller.view;
    [controller.view addSubview:label];
    self.window.rootViewController = controller;
    [self.window makeKeyAndVisible];

    dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED, 0), ^{
        NSString *result = [self runMemoryProbe];
        dispatch_async(dispatch_get_main_queue(), ^{
            label.text = result;
            NSLog(@"WWHD_MEMORY_PROBE_RESULT %@", [result stringByReplacingOccurrencesOfString:@"\n" withString:@" | "]);
        });
    });
    return YES;
}

- (NSString *)runMemoryProbe {
    gPageSize = (size_t)getpagesize();
    if (!gPageSize || (gPageSize & (gPageSize - 1)) != 0) {
        return @"FAIL: invalid host page size";
    }

    mach_vm_address_t address = 0x200000000000ULL;
    kern_return_t allocation = mach_vm_allocate(mach_task_self(), &address, 0x100000000ULL, VM_FLAGS_FIXED);
    if (allocation != KERN_SUCCESS || address != 0x200000000000ULL) {
        return [NSString stringWithFormat:@"FAIL: fixed 4 GiB reservation (Mach error %d)", allocation];
    }
    gGuestBase = reinterpret_cast<uint8_t *>(static_cast<uintptr_t>(address));

    if (mprotect(gGuestBase, gPageSize, PROT_NONE) != 0) {
        mach_vm_deallocate(mach_task_self(), address, 0x100000000ULL);
        gGuestBase = nullptr;
        return @"FAIL: null-page guard mprotect";
    }

    struct sigaction action = {};
    action.sa_sigaction = probeSignalHandler;
    action.sa_flags = SA_SIGINFO;
    sigemptyset(&action.sa_mask);
    struct sigaction oldBus = {}, oldSegv = {};
    if (sigaction(SIGBUS, &action, &oldBus) != 0 || sigaction(SIGSEGV, &action, &oldSegv) != 0) {
        mach_vm_deallocate(mach_task_self(), address, 0x100000000ULL);
        gGuestBase = nullptr;
        return @"FAIL: installing SIGBUS/SIGSEGV handlers";
    }

    uint8_t *watchedPage = gGuestBase + (gPageSize * 2);
    if (mprotect(watchedPage, gPageSize, PROT_READ) != 0) {
        sigaction(SIGBUS, &oldBus, nullptr);
        sigaction(SIGSEGV, &oldSegv, nullptr);
        mach_vm_deallocate(mach_task_self(), address, 0x100000000ULL);
        gGuestBase = nullptr;
        return @"FAIL: protecting watched page";
    }

    gWriteFaultHandled = 0;
    *reinterpret_cast<volatile uint8_t *>(watchedPage) = 0x5A;
    bool writeTrackingPassed = gWriteFaultHandled == 1 && *watchedPage == 0x5A;

    sigaction(SIGBUS, &oldBus, nullptr);
    sigaction(SIGSEGV, &oldSegv, nullptr);
    mach_vm_deallocate(mach_task_self(), address, 0x100000000ULL);
    gGuestBase = nullptr;

    if (!writeTrackingPassed) return @"FAIL: protected-page write fault was not handled";
    return [NSString stringWithFormat:@"PASS: 4 GiB fixed reservation\nPASS: null-page guard\nPASS: protected-page write tracking\nHost page size: %lu bytes\nSimulator only — device validation still required", (unsigned long)gPageSize];
}
@end

int main(int argc, char *argv[]) {
    @autoreleasepool {
        return UIApplicationMain(argc, argv, nil, NSStringFromClass([ProbeAppDelegate class]));
    }
}
