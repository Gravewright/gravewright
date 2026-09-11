"""Native dice grammar: evaluate locally, or roll and publish to the table."""
from gravewright.dice.engine import evaluate
from gravewright.dice.services import roll

__all__ = ['evaluate', 'roll']
