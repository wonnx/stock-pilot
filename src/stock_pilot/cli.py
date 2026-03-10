"""CLI entry point for stock-pilot."""

from __future__ import annotations

import argparse
import logging
import sys

from rich.console import Console
from rich.table import Table

console = Console()


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def cmd_scan(args: argparse.Namespace) -> None:
    """Run a market scan."""
    from stock_pilot.scanner import Scanner

    scanner = Scanner(skip_news=args.no_news)
    console.print("[bold blue]📡 Stock Pilot — 시장 스캔 시작...[/bold blue]")
    result = scanner.run_sync(send_alerts=not args.dry_run)

    table = Table(title="Trade Signals", show_header=True)
    table.add_column("Symbol", style="cyan", no_wrap=True)
    table.add_column("Direction", style="bold")
    table.add_column("Score", justify="right")
    table.add_column("Confidence")
    table.add_column("Close", justify="right")
    table.add_column("Reasons")

    colors = {"BUY": "green", "SELL": "red", "HOLD": "yellow"}
    for sig in result.signals:
        dir_val = sig.direction.value
        color = colors.get(dir_val, "white")
        table.add_row(
            sig.symbol,
            f"[{color}]{dir_val}[/{color}]",
            f"{sig.score:+.2f}",
            sig.confidence,
            f"${sig.close:.2f}",
            "; ".join(sig.reasons[:2]),
        )

    console.print(table)
    if result.errors:
        console.print(f"[red]오류 {len(result.errors)}건:[/red] {', '.join(result.errors)}")
    if not args.dry_run:
        console.print(f"[green]알림 전송: {result.alerts_sent}건[/green]")


def cmd_backtest(args: argparse.Namespace) -> None:
    """Run backtest for a symbol or all watchlist symbols."""
    from stock_pilot.backtest.engine import BacktestEngine
    from stock_pilot.data.fetcher import fetcher
    from stock_pilot.data.watchlist import watchlist

    bt = BacktestEngine()
    symbols = [args.symbol.upper()] if args.symbol else watchlist.symbols

    console.print(f"[bold blue]📊 백테스트 실행: {len(symbols)}개 종목[/bold blue]")

    table = Table(title="Backtest Results (1Y)")
    table.add_column("Symbol")
    table.add_column("Trades", justify="right")
    table.add_column("Win Rate", justify="right")
    table.add_column("Total Return", justify="right")
    table.add_column("Max DD", justify="right")
    table.add_column("Avg Trade", justify="right")

    for sym in symbols:
        df = fetcher.get_ohlcv(sym, period="2y", interval="1d")
        if df.empty:
            continue
        res = bt.run(sym, df)
        ret_color = "green" if res.total_return_pct > 0 else "red"
        table.add_row(
            sym,
            str(res.total_trades),
            f"{res.win_rate:.1%}",
            f"[{ret_color}]{res.total_return_pct:+.1%}[/{ret_color}]",
            f"{res.max_drawdown_pct:.1%}",
            f"{res.avg_trade_pct:+.2%}",
        )

    console.print(table)


def cmd_watchlist(args: argparse.Namespace) -> None:
    """Manage the watchlist."""
    from stock_pilot.data.watchlist import watchlist

    if args.add:
        for sym in args.add:
            watchlist.add(sym)
            console.print(f"[green]추가: {sym.upper()}[/green]")
    elif args.remove:
        for sym in args.remove:
            watchlist.remove(sym)
            console.print(f"[red]제거: {sym.upper()}[/red]")
    else:
        console.print("[bold]현재 Watchlist:[/bold]")
        for sym in watchlist.symbols:
            console.print(f"  • {sym}")


def cmd_content(args: argparse.Namespace) -> None:
    """Generate short-form content for top signals."""
    from stock_pilot.content.pipeline import ContentPipeline
    from stock_pilot.scanner import Scanner

    pipeline = ContentPipeline(output_dir=args.output_dir)
    upload = args.upload and not args.dry_run

    if args.hot:
        # 핫 주식 자동 선정 모드
        console.print("[bold blue]🔥 핫 주식 자동 선정 중...[/bold blue]")
        r = pipeline.run_hot_stock(upload=upload)
        results = [r] if r else []
    elif args.symbols:
        symbols = [s.upper() for s in args.symbols]
        console.print(f"[bold blue]🎬 숏폼 콘텐츠 생성: {symbols}[/bold blue]")
        results = pipeline.run_for_symbols(symbols, upload=upload)
    else:
        console.print("[bold blue]📡 시그널 스캔 중...[/bold blue]")
        scanner = Scanner(skip_news=False)
        scan_result = scanner.run_sync(send_alerts=False)
        actionable = [s for s in scan_result.signals if s.is_actionable]
        symbols = [s.symbol for s in actionable[: args.top_n]]
        if not symbols:
            console.print("[yellow]오늘 액션 가능한 시그널 없음[/yellow]")
            return
        console.print(f"[bold blue]🎬 숏폼 콘텐츠 생성: {symbols}[/bold blue]")
        results = pipeline.run_for_symbols(symbols, upload=upload)

    table = Table(title="Content Pipeline Results")
    table.add_column("Symbol")
    table.add_column("Content")
    table.add_column("Card")
    table.add_column("TTS")
    table.add_column("Video")
    table.add_column("Reel")
    table.add_column("Errors")

    ok = "[green]✓[/green]"
    ng = "[red]✗[/red]"
    for r in results:
        table.add_row(
            r.symbol,
            ok if r.content_ok else ng,
            ok if r.card_news_ok else ng,
            ok if r.tts_ok else ng,
            ok if r.video_ok else ng,
            ok if r.instagram_reel_ok else ng,
            "; ".join(r.errors[:2]) if r.errors else "",
        )
    console.print(table)


def cmd_schedule(args: argparse.Namespace) -> None:
    """Start the scheduler for periodic scans."""
    from apscheduler.schedulers.blocking import BlockingScheduler
    from stock_pilot.scanner import Scanner
    from stock_pilot.utils.config import config

    interval = args.interval or config.SCAN_INTERVAL_MINUTES
    scanner = Scanner(skip_news=args.no_news)

    console.print(f"[bold blue]⏰ 스케줄러 시작 — {interval}분마다 스캔[/bold blue]")

    scheduler = BlockingScheduler()
    scheduler.add_job(
        lambda: scanner.run_sync(send_alerts=True),
        "interval",
        minutes=interval,
        id="market_scan",
    )

    try:
        scheduler.start()
    except KeyboardInterrupt:
        console.print("[yellow]스케줄러 종료[/yellow]")
        sys.exit(0)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="stock-pilot",
        description="미국 주식 분석 및 알림 서비스",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    # scan
    scan_p = sub.add_parser("scan", help="시장 스캔 실행")
    scan_p.add_argument("--dry-run", action="store_true", help="알림 미발송")
    scan_p.add_argument("--no-news", action="store_true", help="뉴스 분석 스킵")
    scan_p.set_defaults(func=cmd_scan)

    # backtest
    bt_p = sub.add_parser("backtest", help="백테스트 실행")
    bt_p.add_argument("symbol", nargs="?", help="종목 코드 (없으면 전체)")
    bt_p.set_defaults(func=cmd_backtest)

    # watchlist
    wl_p = sub.add_parser("watchlist", help="Watchlist 관리")
    wl_p.add_argument("--add", nargs="+", metavar="SYMBOL")
    wl_p.add_argument("--remove", nargs="+", metavar="SYMBOL")
    wl_p.set_defaults(func=cmd_watchlist)

    # schedule
    sched_p = sub.add_parser("schedule", help="주기적 스캔 시작")
    sched_p.add_argument("--interval", type=int, help="분 단위 간격 (기본: 15)")
    sched_p.add_argument("--no-news", action="store_true")
    sched_p.set_defaults(func=cmd_schedule)

    # content
    content_p = sub.add_parser("content", help="숏폼 콘텐츠 생성")
    content_p.add_argument("symbols", nargs="*", help="종목 코드 (없으면 상위 시그널 종목)")
    content_p.add_argument("--hot", action="store_true", help="핫 주식 자동 선정 후 파이프라인 실행")
    content_p.add_argument("--upload", action="store_true", help="Instagram Reels/YouTube 자동 업로드")
    content_p.add_argument("--dry-run", action="store_true", help="생성만, 업로드 안 함")
    content_p.add_argument("--output-dir", default="output", help="출력 디렉토리")
    content_p.add_argument("--top-n", type=int, default=3, help="상위 N개 종목")
    content_p.set_defaults(func=cmd_content)

    args = parser.parse_args()
    setup_logging(args.verbose)
    args.func(args)


if __name__ == "__main__":
    main()
