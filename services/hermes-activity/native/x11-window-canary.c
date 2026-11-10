#include <X11/Xatom.h>
#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/select.h>
#include <unistd.h>

extern void XCompositeRedirectWindow(Display *, Window, int);

static unsigned int shift_for(unsigned long mask) {
    unsigned int shift = 0;
    while (mask != 0 && (mask & 1ul) == 0) { mask >>= 1; ++shift; }
    return shift;
}

static unsigned long channel(unsigned int value, unsigned long mask) {
    if (mask == 0) return 0;
    unsigned int shift = shift_for(mask);
    return ((unsigned long)value * (mask >> shift) / 255ul) << shift;
}

static unsigned long pixel(Visual *visual, unsigned int red, unsigned int green, unsigned int blue) {
    unsigned long alpha = ~(visual->red_mask | visual->green_mask | visual->blue_mask);
    return channel(red, visual->red_mask) | channel(green, visual->green_mask) | channel(blue, visual->blue_mask) | alpha;
}

static void property(Display *display, Window window, Atom name, Atom type, int format, const unsigned char *value, int count) {
    XChangeProperty(display, window, name, type, format, PropModeReplace, value, count);
}

static void identify(Display *display, Window window, Visual *visual, unsigned long pid) {
    char hostname[256] = {0};
    char instance[] = "native-canary";
    char class_name[] = "NativeCanary";
    gethostname(hostname, sizeof(hostname) - 1);
    Atom wm_type = XInternAtom(display, "_NET_WM_WINDOW_TYPE", False);
    Atom normal = XInternAtom(display, "_NET_WM_WINDOW_TYPE_NORMAL", False);
    Atom wm_pid = XInternAtom(display, "_NET_WM_PID", False);
    Atom machine = XInternAtom(display, "WM_CLIENT_MACHINE", False);
    property(display, window, wm_type, XA_ATOM, 32, (unsigned char *)&normal, 1);
    property(display, window, wm_pid, XA_CARDINAL, 32, (unsigned char *)&pid, 1);
    property(display, window, machine, XA_STRING, 8, (unsigned char *)hostname, (int)strlen(hostname));
    XClassHint hint = {instance, class_name};
    XSetClassHint(display, window, &hint);
    (void)visual;
}

static void mark_foreign(Display *display, Window window) {
    char foreign[] = "foreign-client.invalid";
    Atom machine = XInternAtom(display, "WM_CLIENT_MACHINE", False);
    property(display, window, machine, XA_STRING, 8, (unsigned char *)foreign, (int)strlen(foreign));
}

static void paint(Display *display, Window target, Window sibling, Visual *visual) {
    GC target_gc = XCreateGC(display, target, 0, NULL);
    GC sibling_gc = XCreateGC(display, sibling, 0, NULL);
    XSetForeground(display, target_gc, pixel(visual, 0, 255, 0));
    XFillRectangle(display, target, target_gc, 40, 30, 160, 100);
    XSetForeground(display, sibling_gc, pixel(visual, 0, 0, 255));
    XFillRectangle(display, sibling, sibling_gc, 0, 0, 240, 160);
    XFreeGC(display, target_gc);
    XFreeGC(display, sibling_gc);
}

int main(void) {
    setvbuf(stdout, NULL, _IONBF, 0);
    Display *display = XOpenDisplay(NULL);
    if (display == NULL) return 2;
    XVisualInfo visual_info;
    if (!XMatchVisualInfo(display, DefaultScreen(display), 32, TrueColor, &visual_info)) return 4;
    Window root = RootWindow(display, DefaultScreen(display));
    Colormap colormap = XCreateColormap(display, root, visual_info.visual, AllocNone);
    XSetWindowAttributes attributes = {0};
    attributes.colormap = colormap;
    attributes.background_pixel = 0;
    attributes.border_pixel = 0;
    Window target = XCreateWindow(display, root, 0, 0, 240, 160, 0, visual_info.depth, InputOutput, visual_info.visual, CWColormap | CWBackPixel | CWBorderPixel, &attributes);
    Window sibling = XCreateWindow(display, root, 0, 0, 240, 160, 0, visual_info.depth, InputOutput, visual_info.visual, CWColormap | CWBackPixel | CWBorderPixel, &attributes);
    identify(display, target, visual_info.visual, (unsigned long)getpid());
    identify(display, sibling, visual_info.visual, (unsigned long)getpid());
    XSelectInput(display, target, ExposureMask);
    XSelectInput(display, sibling, ExposureMask);
    XCompositeRedirectWindow(display, target, 0);
    XCompositeRedirectWindow(display, sibling, 0);
    XMapWindow(display, target);
    XMapWindow(display, sibling);
    paint(display, target, sibling, visual_info.visual);
    Atom client_list = XInternAtom(display, "_NET_CLIENT_LIST", False);
    Window windows[2] = {target, sibling};
    property(display, root, client_list, XA_WINDOW, 32, (unsigned char *)windows, 2);
    XSync(display, False);
    printf("READY %lu %lu 240 160\n", target, sibling);
    char command[32];
    int target_alive = 1;
    while (1) {
        while (XPending(display)) {
            XEvent event; XNextEvent(display, &event);
            if (event.type == Expose && target_alive) paint(display, target, sibling, visual_info.visual);
        }
        XFlush(display);
        fd_set inputs; FD_ZERO(&inputs); FD_SET(STDIN_FILENO, &inputs); FD_SET(ConnectionNumber(display), &inputs);
        int high = ConnectionNumber(display) > STDIN_FILENO ? ConnectionNumber(display) : STDIN_FILENO;
        if (select(high + 1, &inputs, NULL, NULL, NULL) < 0) break;
        if (!FD_ISSET(STDIN_FILENO, &inputs)) continue;
        if (fgets(command, sizeof(command), stdin) == NULL) break;
        if (strncmp(command, "UNMAP", 5) == 0) XUnmapWindow(display, target);
        else if (strncmp(command, "REMAP", 5) == 0) XMapWindow(display, target);
        else if (strncmp(command, "DESTROY", 7) == 0) { XDestroyWindow(display, target); target_alive = 0; }
        else if (strncmp(command, "FOREIGN", 7) == 0) mark_foreign(display, target);
        else if (strncmp(command, "QUIT", 4) == 0) break;
        XSync(display, False);
    }
    XDestroyWindow(display, sibling);
    if (target_alive) XDestroyWindow(display, target);
    XFreeColormap(display, colormap);
    XCloseDisplay(display);
    return 0;
}
