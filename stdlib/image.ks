:: image - Image processing via ImageMagick (subprocess)
::
:: Usage:
::   import image;
::   let r = image.resize("input.jpg", "output.jpg", 800, 600);

func convert(args) {
    let full = ["convert"];
    for a in args { full.push(a); }
    let result = system_subprocess_run(full);
    return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode};
}

func info(path) {
    let result = system_subprocess_run(["identify", path]);
    return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode};
}

func resize(input, output, width, height) {
    let args = [input, "-resize", str(width) + "x" + str(height) + "!", output];
    return convert(args);
}

func thumbnail(input, output, size) {
    if size == none { size = 128; }
    let args = [input, "-thumbnail", str(size) + "x" + str(size) + "^", "-gravity", "center", "-extent", str(size) + "x" + str(size), output];
    return convert(args);
}

func format(input, output_format) {
    let ext = output_format;
    let output = input + "." + ext;
    let args = [input, output];
    return convert(args);
}

func grayscale(input, output) {
    let args = [input, "-colorspace", "Gray", output];
    return convert(args);
}

func blur(input, output, radius) {
    if radius == none { radius = 5; }
    let args = [input, "-blur", "0x" + str(radius), output];
    return convert(args);
}

func rotate(input, output, degrees) {
    let args = [input, "-rotate", str(degrees), output];
    return convert(args);
}

func crop(input, output, width, height, x, y) {
    if x == none { x = 0; }
    if y == none { y = 0; }
    let args = [input, "-crop", str(width) + "x" + str(height) + "+" + str(x) + "+" + str(y), output];
    return convert(args);
}

export { info, resize, thumbnail, format, grayscale, blur, rotate, crop };
