#ifndef GX_FILE_COMPAT_H
#define GX_FILE_COMPAT_H

#include <cerrno>

#include <glib/gstdio.h>

static inline int gx_replace_file(const char *tmpfile, const char *target) {
#ifdef _WIN32
    if (g_remove(target) != 0 && errno != ENOENT) {
        return -1;
    }
#endif
    return g_rename(tmpfile, target);
}

#endif // GX_FILE_COMPAT_H
