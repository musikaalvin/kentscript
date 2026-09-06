#!/bin/bash
# Build script for KentScript manpages

MAN_DIR="$(cd "$(dirname "$0")/man" && pwd)"
BUILD_DIR="$MAN_DIR/build"

mkdir -p "$BUILD_DIR"

echo "Building KentScript manpages..."

# Compile man pages to section 1 (user commands)
for file in "$MAN_DIR"/man1/*.1; do
    if [ -f "$file" ]; then
        name=$(basename "$file" .1)
        echo "  Building $name.1 -> $BUILD_DIR/$name.1.gz"
        gzip -c "$file" > "$BUILD_DIR/$name.1.gz" 2>/dev/null || cp "$file" "$BUILD_DIR/$name.1"
    fi
done

# Compile man pages to section 3 (library functions)
for file in "$MAN_DIR"/man3/*.3; do
    if [ -f "$file" ]; then
        name=$(basename "$file" .3)
        echo "  Building $name.3 -> $BUILD_DIR/$name.3.gz"
        gzip -c "$file" > "$BUILD_DIR/$name.3.gz" 2>/dev/null || cp "$file" "$BUILD_DIR/$name.3"
    fi
done

echo ""
echo "Manpages built successfully!"
echo "To install system-wide:"
echo "  sudo cp -r $BUILD_DIR/* /usr/share/man/"
echo ""
echo "To view manpages:"
echo "  man kentscript"
echo "  man kentscript-stdlib"
echo "  man kentscript-malloc"
echo "  man kentscript-syscall"
echo "  man kentscript-ffi"
