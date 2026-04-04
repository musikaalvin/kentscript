import color;

:: Color functions
print(color.red("This is red text"));
print(color.green("This is green text"));
print(color.blue("This is blue text"));
print(color.yellow("This is yellow text"));
print(color.cyan("This is cyan text"));
print(color.magenta("This is magenta text"));
print(color.white("This is white text"));

:: Bold colors
print(color.bold(color.red("Bold red")));

:: Background colors
print(color.bg_yellow(color.black("Black on yellow")));

:: Combinations
print(color.bold(color.underline(color.green("Bold underlined green"))));

:: Reset styling
print(color.red("Red") + " - Normal text");
