/*
 * Small dlopen compatibility shim for the Windows standalone build.
 */

#pragma once

#ifndef SRC_HEADERS_GX_DLCOMPAT_H_
#define SRC_HEADERS_GX_DLCOMPAT_H_

#ifdef _WIN32

#include <gmodule.h>

#ifndef RTLD_NOW
#define RTLD_NOW 1
#endif
#ifndef RTLD_LOCAL
#define RTLD_LOCAL 2
#endif

static inline const char*& gx_dlerror_slot() {
    static thread_local const char *last_error = nullptr;
    return last_error;
}

static inline void *dlopen(const char *filename, int flags) {
    GModuleFlags module_flags = G_MODULE_BIND_LOCAL;
    if ((flags & RTLD_NOW) == 0) {
        module_flags = static_cast<GModuleFlags>(module_flags | G_MODULE_BIND_LAZY);
    }
    GModule *module = g_module_open(filename, module_flags);
    gx_dlerror_slot() = module ? nullptr : g_module_error();
    return module;
}

static inline void *dlsym(void *handle, const char *symbol) {
    gpointer target = nullptr;
    if (!g_module_symbol(static_cast<GModule*>(handle), symbol, &target)) {
        gx_dlerror_slot() = g_module_error();
        return nullptr;
    }
    gx_dlerror_slot() = nullptr;
    return target;
}

static inline int dlclose(void *handle) {
    gboolean closed = g_module_close(static_cast<GModule*>(handle));
    gx_dlerror_slot() = closed ? nullptr : g_module_error();
    return closed ? 0 : 1;
}

static inline const char *dlerror() {
    const char *error = gx_dlerror_slot();
    gx_dlerror_slot() = nullptr;
    return error;
}

#else

#include <dlfcn.h>

#endif

#endif  // SRC_HEADERS_GX_DLCOMPAT_H_
