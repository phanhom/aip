"""AIP command-line interface.

Usage:
    aip bridge --agent <url> --platform <url> --secret <key>

All flags support environment variable overrides with AIP_BRIDGE_ prefix:
    AIP_BRIDGE_AGENT, AIP_BRIDGE_PLATFORM, AIP_BRIDGE_SECRET, etc.
"""

from __future__ import annotations

import argparse
import os
import sys

__all__ = ["main"]


def _env(name: str, default: str | None = None) -> str | None:
    """Read from AIP_BRIDGE_<NAME> or AIP_<NAME> env vars."""
    return os.environ.get(f"AIP_BRIDGE_{name}", os.environ.get(f"AIP_{name}", default))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="aip",
        description="AIP Protocol — command-line tools for agent interoperability",
    )
    parser.add_argument("--version", action="store_true", help="Show version and exit")
    sub = parser.add_subparsers(dest="command")

    # ── bridge subcommand ─────────────────────────────────────────────
    br = sub.add_parser(
        "bridge",
        help="Bridge any agent to an AIP platform with one command",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Universal agent-to-AIP bridge.\n\n"
            "Connects any agent — HTTP, WebSocket, subprocess — to an AIP\n"
            "management platform. Protocol is auto-detected from the URL scheme.\n\n"
            "Examples:\n"
            "  aip bridge --agent http://localhost:8080/chat \\\n"
            "      --platform https://hive.example.com --secret sk-xxx\n"
            "  aip bridge --agent ws://10.0.0.5:18789 \\\n"
            "      --platform https://hive.example.com --secret sk-xxx\n"
        ),
    )

    g = br.add_argument_group("agent connection")
    g.add_argument(
        "--agent",
        required=not bool(_env("AGENT")),
        default=_env("AGENT"),
        metavar="URL",
        help="Agent URL. Scheme determines protocol: http(s)://, ws(s)://, stdio:cmd",
    )
    g.add_argument(
        "--agent-secret",
        default=_env("AGENT_SECRET"),
        metavar="KEY",
        help="Secret/token for authenticating TO the external agent",
    )
    g.add_argument(
        "--protocol",
        default=_env("PROTOCOL"),
        choices=["http", "ws", "stdio"],
        help="Override protocol auto-detection",
    )
    g.add_argument(
        "--api-format",
        default=_env("API_FORMAT", "generic"),
        choices=["generic", "openai", "anthropic", "raw"],
        help="Agent API message format (default: generic)",
    )
    g.add_argument(
        "--timeout",
        type=float,
        default=float(_env("TIMEOUT", "120")),
        metavar="SEC",
        help="Agent call timeout in seconds (default: 120)",
    )

    g = br.add_argument_group("platform registration")
    g.add_argument(
        "--platform",
        default=_env("PLATFORM"),
        metavar="URL",
        help="AIP platform URL to register with (omit for standalone mode)",
    )
    g.add_argument(
        "--secret",
        default=_env("SECRET"),
        metavar="KEY",
        help="Shared secret for platform authentication",
    )
    g.add_argument(
        "--heartbeat",
        type=int,
        default=int(_env("HEARTBEAT", "10")),
        metavar="SEC",
        help="Heartbeat interval in seconds (default: 10)",
    )

    g = br.add_argument_group("agent identity")
    g.add_argument(
        "--name",
        default=_env("NAME"),
        help="Human-readable display name (default: hostname)",
    )
    g.add_argument(
        "--id",
        dest="agent_id",
        default=_env("ID"),
        help="Machine identifier (default: bridge-<hostname>-<port>)",
    )
    g.add_argument(
        "--namespace",
        default=_env("NAMESPACE", "default"),
        help="Logical namespace (default: default)",
    )
    g.add_argument(
        "--role",
        default=_env("ROLE", "worker"),
        help="Agent role (default: worker)",
    )
    g.add_argument(
        "--tags",
        default=_env("TAGS", ""),
        help="Comma-separated capability tags (e.g. code,review,search)",
    )
    g.add_argument("--icon", default=_env("ICON"), metavar="URL", help="Icon URL")
    g.add_argument(
        "--color",
        default=_env("COLOR"),
        metavar="HEX",
        help="Brand color hex (e.g. #4A90D9)",
    )

    g = br.add_argument_group("network")
    g.add_argument(
        "--port",
        type=int,
        default=int(_env("PORT", "9090")),
        help="Local AIP bridge port (default: 9090)",
    )
    g.add_argument(
        "--host",
        default=_env("HOST", "0.0.0.0"),
        help="Bind address (default: 0.0.0.0)",
    )
    g.add_argument(
        "--public-url",
        default=_env("PUBLIC_URL"),
        metavar="URL",
        help="Public URL override — use when behind NAT, tunnel, or reverse proxy",
    )

    # ── dispatch ──────────────────────────────────────────────────────
    args = parser.parse_args(argv)

    if args.version:
        from aip import __version__

        print(f"aip-protocol {__version__}")
        return

    if args.command == "bridge":
        from aip.bridge import BridgeConfig, run_bridge

        config = BridgeConfig(
            agent_url=args.agent,
            platform_url=args.platform,
            secret=args.secret,
            agent_secret=args.agent_secret,
            agent_id=args.agent_id,
            name=args.name,
            namespace=args.namespace,
            role=args.role,
            tags=[t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else [],
            icon_url=args.icon,
            color=args.color,
            port=args.port,
            host=args.host,
            public_url=args.public_url,
            protocol=args.protocol,
            api_format=args.api_format,
            timeout=args.timeout,
            heartbeat_interval=args.heartbeat,
        )
        run_bridge(config)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
