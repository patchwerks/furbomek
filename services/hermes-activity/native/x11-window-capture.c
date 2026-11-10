#include <X11/Xatom.h>
#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include "window-frame.h"

extern Bool XCompositeQueryExtension(Display *, int *, int *);
extern Status XCompositeQueryVersion(Display *, int *, int *);
extern void XCompositeRedirectWindow(Display *, Window, int);
extern void XCompositeUnredirectWindow(Display *, Window, int);
extern Pixmap XCompositeNameWindowPixmap(Display *, Window);

enum { CompositeRedirectAutomatic = 0, MaxDimension = 4096 };
static int x_error;
static uint64_t sequence;
static Window active_window;
static int active_invalid;

static int on_x_error(Display *display, XErrorEvent *event) {
    (void)display; (void)event; x_error = 1; return 0;
}

static int u32_property(Display *display, Window window, Atom property, unsigned long *value) {
    Atom type;
    int format;
    unsigned long count, after;
    unsigned char *raw = NULL;
    int result = XGetWindowProperty(display, window, property, 0, 1, False, XA_CARDINAL, &type, &format, &count, &after, &raw);
    int valid = result == Success && type == XA_CARDINAL && format == 32 && count == 1 && raw != NULL;
    if (valid) *value = *(unsigned long *)raw;
    XFree(raw);
    return valid;
}

static int atom_property_contains(Display *display, Window window, Atom property, Atom wanted) {
    Atom type;
    int format;
    unsigned long count, after;
    Atom *atoms = NULL;
    int result = XGetWindowProperty(display, window, property, 0, 32, False, XA_ATOM, &type, &format, &count, &after, (unsigned char **)&atoms);
    int found = result == Success && type == XA_ATOM && format == 32;
    if (found) { found = 0; for (unsigned long index = 0; index < count; ++index) if (atoms[index] == wanted) found = 1; }
    XFree(atoms);
    return found;
}

static int text_property_equals(Display *display, Window window, Atom property, const char *expected) {
    Atom type;
    int format;
    unsigned long count, after;
    unsigned char *raw = NULL;
    int result = XGetWindowProperty(display, window, property, 0, 128, False, AnyPropertyType, &type, &format, &count, &after, &raw);
    int valid = result == Success && raw != NULL && format == 8 && strncmp((char *)raw, expected, count) == 0 && strlen(expected) == count;
    XFree(raw);
    return valid;
}

static int local_machine(Display *display, Window window, Atom machine_atom) {
    char hostname[256] = {0};
    if (gethostname(hostname, sizeof(hostname) - 1) != 0) return 0;
    return text_property_equals(display, window, machine_atom, hostname) || text_property_equals(display, window, machine_atom, "localhost");
}

static int local_process(unsigned long pid) {
    char path[64];
    char line[256];
    unsigned long uid = 0;
    snprintf(path, sizeof(path), "/proc/%lu/status", pid);
    FILE *status = fopen(path, "r");
    if (status == NULL) return 0;
    int found = 0;
    while (fgets(line, sizeof(line), status) != NULL) {
        if (sscanf(line, "Uid:\t%lu", &uid) == 1) { found = uid == (unsigned long)getuid(); break; }
    }
    fclose(status); return found;
}

static int in_client_list(Display *display, Window window) {
    Window root = DefaultRootWindow(display);
    Atom list = XInternAtom(display, "_NET_CLIENT_LIST", True);
    Atom type;
    int format;
    unsigned long count, after;
    Window *windows = NULL;
    if (list == None || XGetWindowProperty(display, root, list, 0, 65536, False, XA_WINDOW, &type, &format, &count, &after, (unsigned char **)&windows) != Success || type != XA_WINDOW || format != 32) {
        XFree(windows);
        return 0;
    }
    int found = 0;
    for (unsigned long index = 0; index < count; ++index) if (windows[index] == window) found = 1;
    XFree(windows);
    return found;
}

static int valid_window(Display *display, Window window, int require_client_list, XWindowAttributes *attributes) {
    Atom type = XInternAtom(display, "_NET_WM_WINDOW_TYPE", True);
    Atom normal = XInternAtom(display, "_NET_WM_WINDOW_TYPE_NORMAL", True);
    Atom pid_atom = XInternAtom(display, "_NET_WM_PID", True);
    Atom machine = XInternAtom(display, "WM_CLIENT_MACHINE", True);
    unsigned long pid = 0;
    x_error = 0;
    int valid = XGetWindowAttributes(display, window, attributes) != 0;
    XSync(display, False);
    valid = valid && !x_error && attributes->class == InputOutput && attributes->map_state == IsViewable && !attributes->override_redirect;
    valid = valid && attributes->visual != NULL && attributes->visual->class == TrueColor && attributes->visual->red_mask != 0 && attributes->visual->green_mask != 0 && attributes->visual->blue_mask != 0;
    valid = valid && type != None && normal != None && pid_atom != None && machine != None && atom_property_contains(display, window, type, normal);
    valid = valid && u32_property(display, window, pid_atom, &pid) && pid > 0 && local_process(pid) && local_machine(display, window, machine);
    valid = valid && (!require_client_list || in_client_list(display, window));
    valid = valid && attributes->width > 0 && attributes->height > 0 && attributes->width <= MaxDimension && attributes->height <= MaxDimension;
    return valid;
}

static void token(char *value) {
    for (char *cursor = value; *cursor != '\0'; ++cursor) if (*cursor == '\t' || *cursor == '\n' || *cursor == '\r' || *cursor == ' ') *cursor = '_';
}

static int list_windows(Display *display) {
    Window root = DefaultRootWindow(display);
    Atom list = XInternAtom(display, "_NET_CLIENT_LIST", True);
    Atom type;
    int format;
    unsigned long count, after;
    Window *windows = NULL;
    if (list == None || XGetWindowProperty(display, root, list, 0, 65536, False, XA_WINDOW, &type, &format, &count, &after, (unsigned char **)&windows) != Success || type != XA_WINDOW || format != 32) {
        XFree(windows);
        return 1;
    }
    for (unsigned long index = 0; index < count; ++index) {
        XWindowAttributes attributes;
        if (!valid_window(display, windows[index], 1, &attributes)) continue;
        Atom pid_atom = XInternAtom(display, "_NET_WM_PID", True);
        unsigned long pid = 0;
        XClassHint hint = {0};
        char instance[128] = "-";
        char class_name[128] = "-";
        u32_property(display, windows[index], pid_atom, &pid);
        if (XGetClassHint(display, windows[index], &hint)) {
            if (hint.res_name != NULL) snprintf(instance, sizeof(instance), "%s", hint.res_name);
            if (hint.res_class != NULL) snprintf(class_name, sizeof(class_name), "%s", hint.res_class);
            XFree(hint.res_name);
            XFree(hint.res_class);
        }
        token(instance);
        token(class_name);
        printf("%lu\t%lu\t%d\t%d\t1\t1\t0\t%s\t%s\n", windows[index], pid, attributes.width, attributes.height, instance, class_name);
    }
    XFree(windows);
    fflush(stdout);
    return 0;
}

static void release_target(Display *display) {
    if (active_window != 0) {
        x_error = 0; XCompositeUnredirectWindow(display, active_window, CompositeRedirectAutomatic); XSync(display, False);
    }
    active_window = 0;
    active_invalid = 0;
}

static void drain_events(Display *display) {
    while (XPending(display) > 0) {
        XEvent event;
        XNextEvent(display, &event);
        if (event.type == DestroyNotify || event.type == UnmapNotify) if (event.xany.window == active_window) active_invalid = 1;
    }
}

static int select_target(Display *display, Window window) {
    if (active_window == window) return !active_invalid;
    release_target(display);
    XWindowAttributes attributes;
    if (!valid_window(display, window, 1, &attributes)) return 0;
    x_error = 0;
    XSelectInput(display, window, StructureNotifyMask);
    XCompositeRedirectWindow(display, window, CompositeRedirectAutomatic);
    XSync(display, False);
    if (x_error) { release_target(display); return 0; }
    active_window = window;
    return 1;
}

static int capture(Display *display, Window window) {
    if (!select_target(display, window)) { error_frame("window identity is invalid or lifecycle-ended"); return 1; }
    drain_events(display);
    if (active_invalid) { error_frame("selected window lifecycle ended"); return 1; }
    XWindowAttributes attributes;
    if (!valid_window(display, window, 1, &attributes)) { active_invalid = 1; error_frame("window identity is no longer local and viewable"); return 1; }
    x_error = 0;
    Pixmap pixmap = XCompositeNameWindowPixmap(display, window);
    XSync(display, False);
    if (x_error || pixmap == None) { error_frame("named window pixmap is unavailable"); return 1; }
    Window root;
    int x, y;
    unsigned int width, height, border, depth;
    x_error = 0;
    if (!XGetGeometry(display, pixmap, &root, &x, &y, &width, &height, &border, &depth)) x_error = 1;
    XSync(display, False);
    if (x_error || width < 1 || height < 1 || width > MaxDimension || height > MaxDimension || (size_t)width * height > (size_t)MaxDimension * MaxDimension) { XFreePixmap(display, pixmap); error_frame("named pixmap geometry is invalid"); return 1; }
    XImage *image = XGetImage(display, pixmap, 0, 0, width, height, AllPlanes, ZPixmap);
    XSync(display, False);
    if (x_error || image == NULL) { XFreePixmap(display, pixmap); error_frame("named window image is unavailable"); return 1; }
    size_t pixels = (size_t)width * height;
    unsigned char *rgb = malloc(pixels * 3);
    if (rgb == NULL) { XDestroyImage(image); XFreePixmap(display, pixmap); error_frame("frame allocation failed"); return 1; }
    uint32_t red_mask = (uint32_t)attributes.visual->red_mask;
    uint32_t green_mask = (uint32_t)attributes.visual->green_mask;
    uint32_t blue_mask = (uint32_t)attributes.visual->blue_mask;
    uint32_t alpha_mask = depth >= 32 ? ~(red_mask | green_mask | blue_mask) : 0;
    unsigned int alpha_shift = shift_for(alpha_mask);
    uint32_t alpha_max = alpha_mask >> alpha_shift;
    for (unsigned int row = 0; row < height; ++row) for (unsigned int column = 0; column < width; ++column) {
        uint32_t pixel = (uint32_t)XGetPixel(image, (int)column, (int)row);
        unsigned int alpha = alpha_mask == 0 || alpha_max == 0 ? 255 : ((pixel & alpha_mask) >> alpha_shift) * 255u / alpha_max;
        size_t offset = ((size_t)row * width + column) * 3;
        unsigned char values[3] = {channel(pixel, red_mask), channel(pixel, green_mask), channel(pixel, blue_mask)};
        for (int component = 0; component < 3; ++component) rgb[offset + (size_t)component] = (unsigned char)(values[component] + (32u * (255u - alpha)) / 255u);
    }
    drain_events(display);
    if (active_invalid) { free(rgb); XDestroyImage(image); XFreePixmap(display, pixmap); error_frame("selected window lifecycle ended"); return 1; }
    unsigned char header[HeaderSize] = {'X', 'C', 'A', 'P', 0, 1, 0, 0};
    put_u32(header + 8, width); put_u32(header + 12, height); put_u32(header + 16, (uint32_t)(pixels * 3)); put_u64(header + 20, ++sequence);
    fwrite(header, sizeof(header), 1, stdout); fwrite(rgb, pixels * 3, 1, stdout); fflush(stdout);
    free(rgb); XDestroyImage(image); XFreePixmap(display, pixmap);
    return 0;
}

int main(int argc, char **argv) {
    if (argc < 2) return 2;
    Display *display = XOpenDisplay(NULL);
    if (display == NULL) return 3;
    XSetErrorHandler(on_x_error);
    int event_base, error_base, major = 0, minor = 0;
    if (!XCompositeQueryExtension(display, &event_base, &error_base) ||
        !XCompositeQueryVersion(display, &major, &minor) || (major == 0 && minor < 2)) {
        XCloseDisplay(display); return 4;
    }
    int result = 0;
    if (strcmp(argv[1], "--list") == 0) result = list_windows(display);
    else if (strcmp(argv[1], "--capture") == 0 && argc == 3) { result = capture(display, (Window)strtoul(argv[2], NULL, 0)); release_target(display); }
    else if (strcmp(argv[1], "--serve") == 0) {
        char command[128];
        while (fgets(command, sizeof(command), stdin) != NULL) {
            if (strncmp(command, "QUIT", 4) == 0) break;
            unsigned long window = 0;
            if (sscanf(command, "CAPTURE %lu", &window) != 1) { error_frame("unknown helper command"); continue; }
            drain_events(display);
            if (window != 0) (void)capture(display, (Window)window);
        }
        release_target(display);
    } else result = 2;
    XCloseDisplay(display);
    return result;
}
