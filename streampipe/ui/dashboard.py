from rich.console import Console
from rich.table import Table
from rich.progress import Progress, TextColumn, BarColumn, DownloadColumn, TransferSpeedColumn, TimeRemainingColumn
from rich.panel import Panel
from rich.text import Text
from streampipe.utils import format_size, format_speed

console = Console()

class Dashboard:
    @staticmethod
    def show_header():
        title_text = Text("StreamPipe 🎬⚡", style="bold cyan")
        subtitle_text = Text("The Advanced Terminal-Based YouTube Downloader", style="italic white")
        console.print(Panel(Text.assemble(title_text, "\n", subtitle_text), expand=False, border_style="cyan"))

    @staticmethod
    def print_error(message: str):
        console.print(f"[bold red]Error:[/bold red] {message}", style="red")

    @staticmethod
    def print_warning(message: str):
        console.print(f"[bold yellow]Warning:[/bold yellow] {message}", style="yellow")

    @staticmethod
    def print_info(message: str):
        console.print(f"[bold blue]Info:[/bold blue] {message}")

    @staticmethod
    def print_success(message: str):
        console.print(f"[bold green]Success:[/bold green] {message}")

    @staticmethod
    def list_qualities(video_title: str, duration: int, streams: dict):
        """Displays available resolutions and audio formats in an elegant grid."""
        console.print(f"\n[bold white]Source:[/bold white] [bold cyan]{video_title}[/bold cyan]")
        if duration:
            mins, secs = divmod(duration, 60)
            hours, mins = divmod(mins, 60)
            duration_str = f"{hours:02d}:{mins:02d}:{secs:02d}" if hours else f"{mins:02d}:{secs:02d}"
            console.print(f"[bold white]Duration:[/bold white] {duration_str}")
        
        # Video streams table
        video_table = Table(title="Available Video Resolutions", border_style="cyan", header_style="bold cyan")
        video_table.add_column("Resolution", style="bold green", justify="left")
        video_table.add_column("Codecs", style="white")
        video_table.add_column("Container", style="yellow")
        video_table.add_column("Bitrate (tbr)", style="magenta")
        video_table.add_column("Est. Size", style="blue")

        video_data = streams.get("video", {})
        # Sort video resolutions descending by height
        sorted_res = sorted(video_data.keys(), key=lambda x: int(x.replace("p", "")) if x.replace("p", "").isdigit() else 0, reverse=True)
        
        for res in sorted_res:
            formats = video_data[res]
            for fmt in formats:
                video_table.add_row(
                    res,
                    f"{fmt['vcodec']} / {fmt['acodec']}",
                    fmt['ext'],
                    f"{fmt['bitrate']:.1f}k" if fmt['bitrate'] else "N/A",
                    format_size(fmt['filesize'])
                )
        
        console.print(video_table)

        # Audio streams table
        audio_table = Table(title="Available Audio Formats", border_style="magenta", header_style="bold magenta")
        audio_table.add_column("Format ID", style="bold magenta")
        audio_table.add_column("Codec", style="white")
        audio_table.add_column("Container", style="yellow")
        audio_table.add_column("Bitrate", style="green")
        audio_table.add_column("Est. Size", style="blue")

        audio_data = streams.get("audio", [])
        for fmt in audio_data:
            audio_table.add_row(
                fmt['format_id'],
                fmt['acodec'],
                fmt['ext'],
                f"{fmt['bitrate']:.1f}k" if fmt['bitrate'] else "N/A",
                format_size(fmt['filesize'])
            )

        console.print(audio_table)

    @staticmethod
    def create_progress_bar() -> Progress:
        """Creates a custom progress bar config suitable for single or parallel downloads."""
        return Progress(
            TextColumn("[bold blue]{task.fields[title]}"),
            TextColumn("[yellow]({task.fields[res]})"),
            BarColumn(bar_width=40, style="grey35", complete_style="green", finished_style="cyan"),
            TextColumn("[bold green]{task.percentage:>3.0f}%"),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            TextColumn("[cyan]{task.fields[status]}"),
            console=console,
            transient=False
        )
