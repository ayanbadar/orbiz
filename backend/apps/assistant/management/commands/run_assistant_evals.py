"""
python manage.py run_assistant_evals [--scenario NAME ...] [--list]

Runs the Orbiz AI eval suite (apps/assistant/evals/) against the REAL OpenAI API — every turn
is a real send_turn call, nothing is mocked. Each run creates and then deletes its own
throwaway, isolated store; nothing in the seller's real data is touched. Exits non-zero if any
scenario fails, so this is CI-usable.

This sends real requests to OpenAI and costs real API usage — never run it without the user's
explicit go-ahead.
"""

from django.core.management.base import BaseCommand

from apps.assistant.evals.runner import run_all, validate_schemas
from apps.assistant.evals.scenarios import ALL_SCENARIOS
from apps.assistant.llm import is_configured


class Command(BaseCommand):
    help = "Run the Orbiz AI eval suite against the real OpenAI API (costs real API usage)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--scenario",
            action="append",
            dest="scenarios",
            help="Run only this scenario (repeatable). Default: run all.",
        )
        parser.add_argument(
            "--list", action="store_true", help="List available scenarios and exit — no API calls."
        )
        parser.add_argument(
            "--validate-schemas",
            action="store_true",
            help=(
                "Just submit TOOL_SCHEMAS to OpenAI and confirm it's accepted — one cheap call, "
                "no scenarios run. Use this after any tool schema change, before a full run."
            ),
        )

    def handle(self, *args, **options):
        if options["list"]:
            for s in ALL_SCENARIOS:
                self.stdout.write(f"{s.name}: {s.description}")
            return

        if not is_configured():
            self.stderr.write(self.style.ERROR("OPENAI_API_KEY is not set — nothing to run."))
            raise SystemExit(1)

        if options["validate_schemas"]:
            if not validate_schemas(stream=self.stdout):
                raise SystemExit(1)
            return

        ok = run_all(options["scenarios"], stream=self.stdout)
        if not ok:
            raise SystemExit(1)
