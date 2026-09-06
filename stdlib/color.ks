:: color - Terminal color and styling with full ANSI support

from math import floor;

:: Reset and basic styles
const RESET = "\x1b[0m";
const BOLD = "\x1b[1m";
const DIM = "\x1b[2m";
const ITALIC = "\x1b[3m";
const UNDERLINE = "\x1b[4m";
const BLINK = "\x1b[5m";
const BLINK_FAST = "\x1b[6m";
const REVERSE = "\x1b[7m";
const HIDDEN = "\x1b[8m";
const STRIKETHROUGH = "\x1b[9m";

:: Double underline and framed
const DOUBLE_UNDERLINE = "\x1b[21m";
const FRAMED = "\x1b[51m";
const ENCIRCLED = "\x1b[52m";
const OVERLINED = "\x1b[53m";

:: Standard colors (30-37)
const BLACK = "\x1b[30m";
const RED = "\x1b[31m";
const GREEN = "\x1b[32m";
const YELLOW = "\x1b[33m";
const BLUE = "\x1b[34m";
const MAGENTA = "\x1b[35m";
const CYAN = "\x1b[36m";
const WHITE = "\x1b[37m";
const DEFAULT = "\x1b[39m";

:: Color name to ANSI code mapping (for use in functions)
const _COLOR_MAP = {
    "black": "\x1b[30m",
    "red": "\x1b[31m",
    "green": "\x1b[32m",
    "yellow": "\x1b[33m",
    "blue": "\x1b[34m",
    "magenta": "\x1b[35m",
    "cyan": "\x1b[36m",
    "white": "\x1b[37m",
    "bright_black": "\x1b[90m",
    "bright_red": "\x1b[91m",
    "bright_green": "\x1b[92m",
    "bright_yellow": "\x1b[93m",
    "bright_blue": "\x1b[94m",
    "bright_magenta": "\x1b[95m",
    "bright_cyan": "\x1b[96m",
    "bright_white": "\x1b[97m",
    "gray": "\x1b[90m",
    "grey": "\x1b[90m",
    "orange": "\x1b[38;5;208m",
    "pink": "\x1b[38;5;213m",
    "purple": "\x1b[38;5;135m",
    "brown": "\x1b[38;5;130m",
    "lime": "\x1b[38;5;154m",
    "teal": "\x1b[38;5;51m",
    "gold": "\x1b[38;5;220m",
    "silver": "\x1b[38;5;250m",
    "dim": "\x1b[2m",
    "bold": "\x1b[1m",
    "italic": "\x1b[3m",
    "underline": "\x1b[4m",
};

func _get_color_code(color_name) {
    if color_name == none {
        return "";
    }
    let code = _COLOR_MAP.get(color_name);
    return code != none ? code : "";
}

:: Background colors (40-47)
const BG_BLACK = "\x1b[40m";
const BG_RED = "\x1b[41m";
const BG_GREEN = "\x1b[42m";
const BG_YELLOW = "\x1b[43m";
const BG_BLUE = "\x1b[44m";
const BG_MAGENTA = "\x1b[45m";
const BG_CYAN = "\x1b[46m";
const BG_WHITE = "\x1b[47m";
const BG_DEFAULT = "\x1b[49m";

:: Bright/intense colors (90-97)
const BRIGHT_BLACK = "\x1b[90m";
const BRIGHT_RED = "\x1b[91m";
const BRIGHT_GREEN = "\x1b[92m";
const BRIGHT_YELLOW = "\x1b[93m";
const BRIGHT_BLUE = "\x1b[94m";
const BRIGHT_MAGENTA = "\x1b[95m";
const BRIGHT_CYAN = "\x1b[96m";
const BRIGHT_WHITE = "\x1b[97m";

:: Bright background colors (100-107)
const BG_BRIGHT_BLACK = "\x1b[100m";
const BG_BRIGHT_RED = "\x1b[101m";
const BG_BRIGHT_GREEN = "\x1b[102m";
const BG_BRIGHT_YELLOW = "\x1b[103m";
const BG_BRIGHT_BLUE = "\x1b[104m";
const BG_BRIGHT_MAGENTA = "\x1b[105m";
const BG_BRIGHT_CYAN = "\x1b[106m";
const BG_BRIGHT_WHITE = "\x1b[107m";

:: Color aliases
const GRAY = BRIGHT_BLACK;
const GREY = BRIGHT_BLACK;
const ORANGE = "\x1b[38;5;208m";
const PINK = "\x1b[38;5;213m";
const PURPLE = "\x1b[38;5;135m";
const BROWN = "\x1b[38;5;130m";
const LIME = "\x1b[38;5;154m";
const TEAL = "\x1b[38;5;51m";
const NAVY = "\x1b[38;5;17m";
const MAROON = "\x1b[38;5;52m";
const OLIVE = "\x1b[38;5;58m";
const AQUA = "\x1b[38;5;87m";
const GOLD = "\x1b[38;5;220m";
const SILVER = "\x1b[38;5;250m";

func colored(text, color, bg, attrs) {
    let result = "";

    :: Convert color names to ANSI codes
    let color_code = _get_color_code(color);
    let bg_code = bg != none ? _get_color_code(bg) : "";

    if attrs != none {
        for attr in attrs {
            result = result + attr;
        }
    }

    if color_code != "" {
        result = result + color_code;
    }

    if bg_code != "" {
        result = result + bg_code;
    }

    result = result + text + RESET;
    return result;
}

:: Basic color functions - use color names, not ANSI codes
func red(text) { return colored(text, "red", none, none); }
func green(text) { return colored(text, "green", none, none); }
func yellow(text) { return colored(text, "yellow", none, none); }
func blue(text) { return colored(text, "blue", none, none); }
func magenta(text) { return colored(text, "magenta", none, none); }
func cyan(text) { return colored(text, "cyan", none, none); }
func white(text) { return colored(text, "white", none, none); }
func black(text) { return colored(text, "black", none, none); }

:: Bright color functions
func bright_red(text) { return colored(text, "bright_red", none, none); }
func bright_green(text) { return colored(text, "bright_green", none, none); }
func bright_yellow(text) { return colored(text, "bright_yellow", none, none); }
func bright_blue(text) { return colored(text, "bright_blue", none, none); }
func bright_magenta(text) { return colored(text, "bright_magenta", none, none); }
func bright_cyan(text) { return colored(text, "bright_cyan", none, none); }
func bright_white(text) { return colored(text, "bright_white", none, none); }
func gray(text) { return colored(text, "gray", none, none); }
func grey(text) { return colored(text, "grey", none, none); }

:: Extended color functions
func orange(text) { return colored(text, "orange", none, none); }
func pink(text) { return colored(text, "pink", none, none); }
func purple(text) { return colored(text, "purple", none, none); }
func brown(text) { return colored(text, "brown", none, none); }
func lime(text) { return colored(text, "lime", none, none); }
func teal(text) { return colored(text, "teal", none, none); }
func gold(text) { return colored(text, "gold", none, none); }
func silver(text) { return colored(text, "silver", none, none); }

:: Style functions
func bold(text) { return colored(text, none, none, [BOLD]); }
func dim(text) { return colored(text, none, none, [DIM]); }
func italic(text) { return colored(text, none, none, [ITALIC]); }
func underline(text) { return colored(text, none, none, [UNDERLINE]); }
func blink(text) { return colored(text, none, none, [BLINK]); }
func reverse(text) { return colored(text, none, none, [REVERSE]); }
func hidden(text) { return colored(text, none, none, [HIDDEN]); }
func strikethrough(text) { return colored(text, none, none, [STRIKETHROUGH]); }
func overline(text) { return colored(text, none, none, [OVERLINED]); }

:: Combined style functions
func bold_red(text) { return colored(text, "red", none, [BOLD]); }
func bold_green(text) { return colored(text, "green", none, [BOLD]); }
func bold_yellow(text) { return colored(text, "yellow", none, [BOLD]); }
func bold_blue(text) { return colored(text, "blue", none, [BOLD]); }
func bold_magenta(text) { return colored(text, "magenta", none, [BOLD]); }
func bold_cyan(text) { return colored(text, "cyan", none, [BOLD]); }
func bold_white(text) { return colored(text, "white", none, [BOLD]); }

func underline_red(text) { return colored(text, "red", none, [UNDERLINE]); }
func underline_green(text) { return colored(text, "green", none, [UNDERLINE]); }
func underline_blue(text) { return colored(text, "blue", none, [UNDERLINE]); }

:: RGB color (24-bit true color)
func rgb(r, g, b) {
    return f"\x1b[38;2;{r};{g};{b}m";
}

func bg_rgb(r, g, b) {
    return f"\x1b[48;2;{r};{g};{b}m";
}

:: Basic background color functions
func bg_yellow(text) { return BG_YELLOW + text + RESET; }
func bg_red(text) { return BG_RED + text + RESET; }
func bg_green(text) { return BG_GREEN + text + RESET; }
func bg_blue(text) { return BG_BLUE + text + RESET; }
func bg_magenta(text) { return BG_MAGENTA + text + RESET; }
func bg_cyan(text) { return BG_CYAN + text + RESET; }
func bg_white(text) { return BG_WHITE + text + RESET; }
func bg_black(text) { return BG_BLACK + text + RESET; }
func bg_default(text) { return BG_DEFAULT + text + RESET; }

:: 256-color palette
func color256(code) {
    return f"\x1b[38;5;{code}m";
}

func bg_color256(code) {
    return f"\x1b[48;5;{code}m";
}

:: Gradient text
func gradient(text, start_r, start_g, start_b, end_r, end_g, end_b) {
    let result = "";
    let length = len(text);
    
    for i in range(0, length) {
        let ratio = i / (length - 1);
        let r = start_r + (end_r - start_r) * ratio;
        let g = start_g + (end_g - start_b) * ratio;
        let b = start_b + (end_b - start_b) * ratio;
        
        result = result + rgb(r, g, b) + text[i];
    }
    
    return result + RESET;
}

:: Rainbow text
func rainbow(text) {
    let colors = [RED, YELLOW, GREEN, CYAN, BLUE, MAGENTA];
    let result = "";
    let length = len(text);
    
    for i in range(0, length) {
        let color_idx = i % len(colors);
        result = result + colors[color_idx] + text[i];
    }
    
    return result + RESET;
}

:: Utility functions
func reset() { return RESET; }

func strip_color(text) {
    return regex.sub("\\x1b\\[[0-9;]*m", "", text);
}

func length_without_color(text) {
    return len(strip_color(text));
}

:: Box drawing
func box(text, color, style) {
    let lines = text.split("\n");
    let max_len = 0;
    
    for line in lines {
        let l = length_without_color(line);
        if l > max_len {
            max_len = l;
        }
    }
    
    let top = "╔" + "═" * (max_len + 2) + "╗";
    let bottom = "╚" + "═" * (max_len + 2) + "╝";
    let result = colored(top, color, none, style) + "\n";
    
    for line in lines {
        let padding = " " * (max_len - length_without_color(line));
        result = result + colored("║ ", color, none, style) + line + padding + colored(" ║", color, none, style) + "\n";
    }
    
    result = result + colored(bottom, color, none, style);
    return result;
}

:: Cyberpunk Progress Bar
func progress_bar(percent, width, color) {
    let filled = floor((percent * width) / 100);
    let empty = width - filled;
    let bar = "█" * filled + "░" * empty;
    return colored(bar, color, none, none) + f" {percent}%";
}

func progress_bar_cyber(percent, width, style) {
    let color = style != none ? style : "cyan";
    let color_code = _get_color_code(color);
    let bold_code = "\x1b[1m";
    let filled = floor((percent * width) / 100);
    let empty = width - filled;
    
    let filled_chars = ["▓", "▒", "░"];
    let bar = "";
    for i in 0..filled {
        let char_idx = i % filled_chars.length;
        bar = bar + filled_chars[char_idx];
    }
    for i in 0..empty {
        bar = bar + "░";
    }
    
    let pct = f" {percent:5.1f}% ";
    let arrow = percent < 100 ? "▶" : "█";
    
    return color_code + "╭" + bar + "╮" + bold_code + color_code + pct + color_code + arrow + RESET;
}

func progress_bar_glow(percent, width, color) {
    let filled = floor((percent * width) / 100);
    let empty = width - filled;
    
    let bar = colored("━" * filled, color, none, "bold");
    let empty_bar = colored("─" * empty, "dim", none, none);
    
    let glow = colored("◉", color, none, "bold");
    let pct_str = percent < 10 ? f"0{percent}" : f"{percent}";
    
    return f"┢┧━ {pct_str}% {bar}{empty_bar}▸";
}

func progress_bar_matrix(percent, width) {
    let filled = floor((percent * width) / 100);
    let empty = width - filled;
    
    let bin = "";
    for i in 0..filled {
        let chars = ["█", "▓", "▒", "░"];
        bin = bin + chars[i % chars.length];
    }
    for i in 0..empty {
        bin = bin + "░";
    }
    
    let green_code = _get_color_code("bright_green");
    let bold_code = "\x1b[1m";
    
    return green_code + bin + bold_code + green_code + f" {percent}% " + RESET;
}

func progress_bar_gradient(percent, width) {
    let filled = floor((percent * width) / 100);
    let empty = width - filled;
    
    let gradient_colors = ["red", "yellow", "green", "cyan", "blue", "magenta"];
    let bar = "";
    for i in 0..filled {
        let color_idx = floor((i * gradient_colors.length) / width) % gradient_colors.length;
        bar = bar + colored("▰", gradient_colors[color_idx], none, none);
    }
    for i in 0..empty {
        bar = bar + colored("▱", "dim", none, none);
    }
    
    let left = colored("╔", "cyan", none, none);
    let right = colored("╗", "cyan", none, none);
    let sep = colored("║", "cyan", none, none);
    let pct = colored(f" {percent:5.1f}% ", "cyan", none, "bold");
    
    return left + bar + right + "\n" + sep + pct + sep;
}

func progress_bar_scifi(percent, width, color) {
    let c = color != none ? color : "cyan";
    let filled = floor((percent * width) / 100);
    let empty = width - filled;
    
    let segments = floor(filled / 4);
    let remainder = filled % 4;
    
    let seg_chars = ["▏", "▎", "▍", "▌", "▋", "▊", "▉", "█"];
    let bar = seg_chars[7] * segments;
    if remainder > 0 {
        bar = bar + seg_chars[remainder - 1];
    }
    bar = bar + "░" * empty;
    
    let frame_l = colored("⎣", c, none, none);
    let frame_r = colored("⎤", c, none, none);
    let bracket = colored("⟪", c, none, "bold");
    let pct = colored(f"{percent:05.1f}%", c, none, "bold");
    
    return bracket + " " + frame_l + colored(bar, c, none, none) + frame_r + " " + pct;
}

export {
    RESET, BOLD, DIM, ITALIC, UNDERLINE, BLINK, BLINK_FAST, REVERSE, HIDDEN, STRIKETHROUGH,
    DOUBLE_UNDERLINE, FRAMED, ENCIRCLED, OVERLINED,
    BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE, DEFAULT,
    BG_BLACK, BG_RED, BG_GREEN, BG_YELLOW, BG_BLUE, BG_MAGENTA, BG_CYAN, BG_WHITE, BG_DEFAULT,
    BRIGHT_BLACK, BRIGHT_RED, BRIGHT_GREEN, BRIGHT_YELLOW,
    BRIGHT_BLUE, BRIGHT_MAGENTA, BRIGHT_CYAN, BRIGHT_WHITE,
    BG_BRIGHT_BLACK, BG_BRIGHT_RED, BG_BRIGHT_GREEN, BG_BRIGHT_YELLOW,
    BG_BRIGHT_BLUE, BG_BRIGHT_MAGENTA, BG_BRIGHT_CYAN, BG_BRIGHT_WHITE,
    GRAY, GREY, ORANGE, PINK, PURPLE, BROWN, LIME, TEAL, NAVY, MAROON, OLIVE, AQUA, GOLD, SILVER,
    colored, red, green, yellow, blue, magenta, cyan, white, black,
    bright_red, bright_green, bright_yellow, bright_blue, bright_magenta, bright_cyan, bright_white,
    gray, grey, orange, pink, purple, brown, lime, teal, gold, silver,
    bold, dim, italic, underline, blink, reverse, hidden, strikethrough, overline,
    bold_red, bold_green, bold_yellow, bold_blue, bold_magenta, bold_cyan, bold_white,
    underline_red, underline_green, underline_blue,
    bg_yellow, bg_red, bg_green, bg_blue, bg_magenta, bg_cyan, bg_white, bg_black, bg_default,
    rgb, bg_rgb, color256, bg_color256,
    gradient, rainbow, strip_color, length_without_color, box, progress_bar,
    progress_bar_cyber, progress_bar_glow, progress_bar_matrix, progress_bar_gradient, progress_bar_scifi,
    reset
};
