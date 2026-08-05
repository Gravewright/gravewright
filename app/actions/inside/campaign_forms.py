from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CreateCampaignForm:
    title: str
    description: str = ""


@dataclass
class CampaignIdForm:
    campaign_id: str


@dataclass
class UpdateCampaignForm:
    campaign_id: str
    title: str
    description: str = ""


@dataclass
class DeleteCampaignForm:
    campaign_id: str
    removal_code: str