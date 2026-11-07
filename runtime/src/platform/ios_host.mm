// iOS application sandbox setup. The game data folder is Documents/game so it can be
// copied into the app through the Files app; settings and caches stay in Application Support.
#import <Foundation/Foundation.h>
#include <unistd.h>

extern "C" void wwhd_ios_prepare_paths() {
    @autoreleasepool {
        NSArray<NSString*>* paths = NSSearchPathForDirectoriesInDomains(NSDocumentDirectory, NSUserDomainMask, YES);
        NSString* documents = paths.firstObject;
        if (documents.length == 0) {
            NSLog(@"[iOS] Documents directory is unavailable");
            return;
        }
        NSError* error = nil;
        [[NSFileManager defaultManager] createDirectoryAtPath:documents
                                  withIntermediateDirectories:YES attributes:nil error:&error];
        if (error) NSLog(@"[iOS] cannot prepare Documents: %@", error);
        if (chdir(documents.fileSystemRepresentation) != 0)
            NSLog(@"[iOS] cannot enter Documents: %s", documents.fileSystemRepresentation);
    }
}
