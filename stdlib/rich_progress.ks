::
:: rich_progress - Rich library wrapper for animated progress bars
:: Uses the Python 'rich' library for smooth animations
::

const _RICH_AVAILABLE = true;

:: Import rich
from rich.console import Console;
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn, TimeElapsedColumn, SpinnerColumn;

:: Progress bar with animation
func progress_bar_animated(task_name, total) {
    let console = Console();
    let progress = Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console
    );
    
    return progress;
}

:: Simple animated bar
func animate_simple(description, total) {
    let console = Console();
    let progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console
    );
    return progress;
}

:: Add a task to progress and return the task_id
func add_task(progress, description, total) {
    return progress.add_task(description, total=total);
}

:: Update progress
func update_progress(progress, task_id, advance_amount) {
    progress.update(task_id, advance=advance_amount);
}

:: Start and stop progress display
func start_progress(progress) {
    progress.start();
}

func stop_progress(progress) {
    progress.stop();
}

:: Convenience function - simple one-line progress
func quick_progress(description, total) {
    let console = Console();
    with console.status(f"[bold green]{description}...") as status:
        for i in 0..total {
            status.update(f"{description}: {i}/{total}");
        }
    return "";
}

export {
    progress_bar_animated,
    animate_simple,
    add_task,
    update_progress,
    start_progress,
    stop_progress,
    quick_progress,
};
