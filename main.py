"""CLI para el rastreador de disponibilidad de SheIn.

Subcomandos:
  check-once   Ejecuta una unica pasada de comprobacion (util con cron/systemd).
  run          Bucle infinito que comprueba cada `check_interval_hours`.
  debug        Vuelca captura + HTML de una URL para calibrar los selectores.
"""
from __future__ import annotations

import argparse
import logging
import time

from src.browser_client import dump_debug_snapshot
from src.config import ConfigError, load_config
from src.tracker import run_check_once


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def cmd_check_once(args: argparse.Namespace) -> int:
    config = load_config(args.config, args.env)
    run_check_once(config)
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    config = load_config(args.config, args.env)
    logger = logging.getLogger("run")
    interval_seconds = config.check_interval_hours * 3600
    logger.info(
        "Iniciando bucle: %d producto(s), cada %.2f horas.",
        len(config.products),
        config.check_interval_hours,
    )
    while True:
        try:
            run_check_once(config)
        except Exception:  # noqa: BLE001 - una pasada fallida no debe tumbar el bucle
            logger.exception("Fallo durante la comprobacion, se reintentara en el siguiente ciclo.")
        logger.info("Esperando %.2f horas hasta la proxima comprobacion.", config.check_interval_hours)
        time.sleep(interval_seconds)


def cmd_debug(args: argparse.Namespace) -> int:
    screenshot_path, html_path, final_url = dump_debug_snapshot(
        args.url, args.output, headless=not args.headful
    )
    print(f"URL final tras la navegacion: {final_url}")
    print(f"Captura guardada en: {screenshot_path}")
    print(f"HTML guardado en:    {html_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rastreador de disponibilidad de tallas en SheIn")
    parser.add_argument("--verbose", action="store_true", help="Logging en modo debug")
    subparsers = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--config", default="config.yaml", help="Ruta al config.yaml")
    common.add_argument("--env", default=None, help="Ruta al archivo .env (por defecto: .env)")

    check_once = subparsers.add_parser("check-once", parents=[common], help="Una sola comprobacion")
    check_once.set_defaults(func=cmd_check_once)

    run_cmd = subparsers.add_parser("run", parents=[common], help="Bucle continuo")
    run_cmd.set_defaults(func=cmd_run)

    debug_cmd = subparsers.add_parser("debug", help="Volcar captura/HTML de una URL para calibrar selectores")
    debug_cmd.add_argument("--url", required=True)
    debug_cmd.add_argument("--output", default="debug")
    debug_cmd.add_argument("--headful", action="store_true", help="Mostrar el navegador (requiere entorno grafico)")
    debug_cmd.set_defaults(func=cmd_debug)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    _setup_logging(args.verbose)
    try:
        return args.func(args)
    except ConfigError as exc:
        logging.getLogger("main").error(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
