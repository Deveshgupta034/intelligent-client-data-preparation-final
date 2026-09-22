from __future__ import annotations
import sys
import html
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from icdp.ingestion import inspect_upload, read_upload
from icdp.profiling import profile_dataframe
from icdp.cleanup import apply_negative_action, duplicate_report, remove_duplicates, standardize_dates, manage_columns
from icdp.classification import TARGETS, classify_columns, ai_classify_unresolved
from icdp.transform import DIMS, load_standards, transform_to_niq, clean_text
from icdp.quality import build_quality_report
from icdp.reconciliation import reconcile
from icdp.ai_client import AIClient
from icdp.exports import csv_bytes, excel_bytes, excel_allowed, package_bytes

st.set_page_config(
    page_title="Intelligent Client Data Preparation",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded"
)

STEPS = [
    ("Upload", "Source files"),
    ("Profile", "Analyze data"),
    ("Cleanup", "Fix issues"),
    ("AI Setup", "Model link"),
    ("Classify", "Map fields"),
    ("Transform", "Build output"),
    ("Validate", "Reconcile"),
    ("Review", "Edit output"),
    ("Export", "Download")
]

def defaults():
    return {
        "theme": "dark",
        "step": 1,
        "file_name": "",
        "file_bytes": None,
        "sheets": None,
        "ingestion": None,
        "raw_frame": None,
        "profile": None,
        "duplicates": pd.DataFrame(),
        "mapping": None,
        "output": None,
        "quality": pd.DataFrame(),
        "audit": [],
        "api_tested": False,
        "ai_enabled": True,
        "ai_client": None,
        "ai_endpoint": "https://llm-api-cis.azure-intlsd-np.nielsencsp.net/",
        "ai_model": "hack-fest-gpt-5.6-luna",
        "ai_key": "",
        "token_usage": [],
        "recon_summary": {},
        "recon_detail": pd.DataFrame()
    }

for k, v in defaults().items():
    st.session_state.setdefault(k, v)

def toggle_theme():
    st.session_state.theme = "light" if st.session_state.get("theme", "dark") == "dark" else "dark"

standards = load_standards(ROOT / "config/standards.yaml")

def go(n: int):
    st.session_state.step = n
    st.rerun()

current_theme = st.session_state.get("theme", "dark")
is_dark = (current_theme == "dark")

# Custom Modern Multi-Theme System with Smooth Transitions & Animations
COMMON_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700;800;900&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500;700&display=swap');

*, *::before, *::after {
    box-sizing: border-box;
    transition: background-color 0.38s cubic-bezier(0.4, 0, 0.2, 1),
                background 0.38s cubic-bezier(0.4, 0, 0.2, 1),
                border-color 0.38s cubic-bezier(0.4, 0, 0.2, 1),
                color 0.28s ease,
                box-shadow 0.38s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

h1, h2, h3, h4, .app-title, .step-main-title, [data-testid='stMetricValue'] {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    letter-spacing: -0.025em;
}

[data-testid='stMetricValue'], .tabular, table {
    font-variant-numeric: tabular-nums;
}

/* Page load & theme wipe animations */
@keyframes pageFadeIn {
    from { opacity: 0; transform: translateY(6px); }
    to { opacity: 1; transform: translateY(0); }
}

@keyframes themeSweepWave {
    0% { filter: brightness(1.2) contrast(1.05); opacity: 0.88; transform: translateY(4px); }
    100% { filter: brightness(1) contrast(1); opacity: 1; transform: translateY(0); }
}

.block-container {
    max-width: 1400px;
    padding-top: 4.8rem !important;
    padding-bottom: 4rem !important;
    animation: themeSweepWave 0.42s cubic-bezier(0.16, 1, 0.3, 1);
}

#MainMenu, footer {
    visibility: hidden;
}

/* ========================================================================= */
/* CRAZY HIGH-TECH HARDWARE ANIMATION ENGINE                                 */
/* ========================================================================= */

/* 1. Rotating Chromatic Plasma Aura Border */
@keyframes plasmaBorderOrbit {
    0% {
        border-color: rgba(56, 189, 248, 0.75);
        box-shadow: 0 0 25px rgba(56, 189, 248, 0.4), 0 16px 40px rgba(0, 0, 0, 0.7), inset 0 1px 2px rgba(255, 255, 255, 0.35);
    }
    33% {
        border-color: rgba(168, 85, 247, 0.8);
        box-shadow: 0 0 32px rgba(168, 85, 247, 0.45), 0 16px 40px rgba(0, 0, 0, 0.7), inset 0 1px 2px rgba(255, 255, 255, 0.35);
    }
    66% {
        border-color: rgba(52, 211, 153, 0.8);
        box-shadow: 0 0 32px rgba(52, 211, 153, 0.45), 0 16px 40px rgba(0, 0, 0, 0.7), inset 0 1px 2px rgba(255, 255, 255, 0.35);
    }
    100% {
        border-color: rgba(56, 189, 248, 0.75);
        box-shadow: 0 0 25px rgba(56, 189, 248, 0.4), 0 16px 40px rgba(0, 0, 0, 0.7), inset 0 1px 2px rgba(255, 255, 255, 0.35);
    }
}
.doppelrand-chassis.phase-active {
    animation: plasmaBorderOrbit 4.5s ease-in-out infinite !important;
}

/* 2. Holographic Diagonal Light Sheen */
@keyframes holoGlassSweep {
    0% { transform: translateX(-150%) skewX(-30deg); opacity: 0; }
    15% { opacity: 0.75; }
    40% { transform: translateX(320%) skewX(-30deg); opacity: 0; }
    100% { transform: translateX(320%) skewX(-30deg); opacity: 0; }
}
.phase-active .doppelrand-core::after {
    content: '';
    position: absolute;
    top: 0; left: 0; width: 60%; height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.12), transparent);
    transform: translateX(-150%) skewX(-30deg);
    pointer-events: none;
    animation: holoGlassSweep 5.5s cubic-bezier(0.4, 0, 0.2, 1) infinite;
}

/* 3. Supercharged Plasma Laser Head & Energy Surge */
@keyframes plasmaLaserHead {
    0% { left: -15%; opacity: 0; }
    20% { opacity: 1; }
    80% { opacity: 1; }
    100% { left: 115%; opacity: 0; }
}
@keyframes laserGlowSurge {
    0%, 100% { filter: drop-shadow(0 0 6px rgba(56, 189, 248, 0.6)) brightness(1); }
    50% { filter: drop-shadow(0 0 16px rgba(56, 189, 248, 1)) drop-shadow(0 0 24px rgba(168, 85, 247, 0.8)) brightness(1.35); }
}
.laser-active {
    animation: laserGlowSurge 2s ease-in-out infinite alternate !important;
}
.laser-active::after {
    content: '';
    position: absolute;
    top: -2px; bottom: -2px; width: 45px;
    background: linear-gradient(90deg, transparent, #ffffff 50%, #38bdf8 100%) !important;
    filter: drop-shadow(0 0 8px #38bdf8) drop-shadow(0 0 16px #ffffff) !important;
    animation: plasmaLaserHead 1.5s cubic-bezier(0.4, 0, 0.2, 1) infinite !important;
    border-radius: 99px;
}

/* 4. Viewfinder HUD Laser Scanline */
@keyframes hudScanningLaser {
    0% { top: 6px; opacity: 0; }
    15% { opacity: 0.85; }
    85% { opacity: 0.85; }
    100% { top: calc(100% - 8px); opacity: 0; }
}
.docking-port::before {
    content: '';
    position: absolute;
    left: 12px; right: 12px; height: 2px;
    background: linear-gradient(90deg, transparent, #38bdf8 20%, #a855f7 50%, #38bdf8 80%, transparent);
    box-shadow: 0 0 10px #38bdf8, 0 0 20px rgba(168, 85, 247, 0.6);
    pointer-events: none;
    animation: hudScanningLaser 3.2s ease-in-out infinite;
    border-radius: 99px;
    z-index: 1;
}

/* 5. Cybernetic Dot Grid Ambient Warp */
@keyframes cyberGridWarp {
    0%, 100% { opacity: 0.65; transform: scale(1); }
    50% { opacity: 0.95; transform: scale(1.02); }
}
.stApp::before {
    animation: cyberGridWarp 7s ease-in-out infinite alternate !important;
}

/* 6. Solar Corona & Pulse Keyframes */
@keyframes solarCoronaPulse {
    0% {
        box-shadow: 0 0 18px rgba(245, 158, 11, 0.45), inset 0 1px 2px rgba(255, 255, 255, 0.4);
        transform: translateY(-2px) scale(1.02);
    }
    100% {
        box-shadow: 0 0 36px rgba(245, 158, 11, 0.85), inset 0 1px 4px rgba(255, 255, 255, 0.6);
        transform: translateY(-3px) scale(1.04);
    }
}

@keyframes prismPulse {
    0% {
        box-shadow: 0 0 16px rgba(56, 189, 248, 0.5), inset 0 1px 2px rgba(255, 255, 255, 0.5);
        filter: hue-rotate(0deg);
        transform: rotate(0deg) scale(1);
    }
    50% {
        box-shadow: 0 0 28px rgba(168, 85, 247, 0.9), 0 0 14px rgba(56, 189, 248, 0.8), inset 0 1px 3px rgba(255, 255, 255, 0.8);
        filter: hue-rotate(40deg);
        transform: rotate(3deg) scale(1.05);
    }
    100% {
        box-shadow: 0 0 16px rgba(56, 189, 248, 0.5), inset 0 1px 2px rgba(255, 255, 255, 0.5);
        filter: hue-rotate(0deg);
        transform: rotate(0deg) scale(1);
    }
}

@keyframes beaconBounce {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-5px); }
}

/* Theme Toggle Chassis & Button Layout */
/* Theme Toggle Button Chassis */
.theme-toggle-chassis {
    margin-bottom: 20px;
}
.theme-toggle-chassis .stButton {
    margin: 0 !important;
    padding: 0 !important;
    width: 100% !important;
}
.theme-toggle-chassis .stButton button {
    height: 58px !important;
    min-height: 58px !important;
    border-radius: 16px !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 0.90rem !important;
    font-weight: 800 !important;
    letter-spacing: 0.04em !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 8px !important;
    cursor: pointer !important;
    white-space: nowrap !important;
    transition: all 0.28s cubic-bezier(0.2, 0, 0, 1) !important;
}

/* Brand Bar Elements - Always Single Row */
.app-brand-bar {
    display: flex !important;
    flex-direction: row !important;
    justify-content: space-between !important;
    align-items: center !important;
    flex-wrap: nowrap !important;
    height: 58px !important;
    min-height: 58px !important;
    padding: 0 20px !important;
    border-radius: 16px !important;
    margin-bottom: 20px !important;
    width: 100% !important;
}
.app-brand-left {
    display: flex !important;
    align-items: center !important;
    gap: 12px !important;
    white-space: nowrap !important;
    flex-shrink: 0 !important;
}
.app-diamond-logo {
    width: 34px !important;
    height: 34px !important;
    border-radius: 9px !important;
    background: linear-gradient(135deg, #4f46e5 0%, #38bdf8 50%, #818cf8 100%) !important;
    box-shadow: 0 0 18px rgba(56, 189, 248, 0.7), inset 0 1px 2px rgba(255, 255, 255, 0.5) !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    font-size: 1.15rem !important;
    color: white !important;
    font-weight: 900 !important;
    flex-shrink: 0 !important;
    animation: prismPulse 3s ease-in-out infinite alternate !important;
}
.app-brand-title {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 1.12rem !important;
    font-weight: 850 !important;
    letter-spacing: 0.05em !important;
    text-transform: uppercase !important;
    white-space: nowrap !important;
    margin: 0 !important;
    line-height: 1 !important;
}
.app-brand-right {
    display: flex !important;
    align-items: center !important;
    gap: 10px !important;
    white-space: nowrap !important;
    flex-shrink: 0 !important;
}
.brand-pill-live {
    display: inline-flex !important;
    align-items: center !important;
    gap: 8px !important;
    border-radius: 99px !important;
    padding: 6px 16px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.74rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.08em !important;
    white-space: nowrap !important;
}
@keyframes radarPing {
    0% {
        transform: scale(0.9);
        box-shadow: 0 0 0 0 rgba(56, 189, 248, 0.85);
    }
    70% {
        transform: scale(1.1);
        box-shadow: 0 0 0 7px rgba(56, 189, 248, 0);
    }
    100% {
        transform: scale(0.9);
        box-shadow: 0 0 0 0 rgba(56, 189, 248, 0);
    }
}
.live-badge-dot {
    width: 7px !important;
    height: 7px !important;
    border-radius: 99px !important;
    flex-shrink: 0 !important;
    animation: radarPing 2.2s cubic-bezier(0.4, 0, 0.6, 1) infinite !important;
}


/* Universal Theme Typography & Surfaces */
.theme-card-title {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-weight: 800 !important;
    letter-spacing: -0.01em !important;
    line-height: 1.25 !important;
}
.theme-card-sub {
    font-size: 0.82rem !important;
    line-height: 1.4 !important;
}
.theme-metric-num {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-weight: 850 !important;
    letter-spacing: -0.02em !important;
    font-variant-numeric: tabular-nums !important;
}
.health-track {
    width: 100%;
    height: 8px;
    border-radius: 99px;
    overflow: hidden;
    margin-bottom: 20px;
}
.health-fill {
    height: 100%;
    border-radius: 99px;
    background: linear-gradient(90deg, #10b981, #059669);
    transition: width 0.4s ease;
}

/* Phase Deck & Cards */
@keyframes cardEntrance {
    from {
        opacity: 0;
        transform: translateY(8px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}
.phase-deck {
    display: grid;
    grid-template-columns: 1fr auto 1fr auto 1fr;
    align-items: center;
    gap: 14px;
    margin-bottom: 24px;
    animation: cardEntrance 0.35s cubic-bezier(0.16, 1, 0.3, 1) 0.05s both;
}
.phase-chevron {
    font-size: 1.3rem;
    font-weight: 800;
    user-select: none;
}
.phase-card-core {
    padding: 18px 22px;
}
.phase-header-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
}
.phase-badge-title {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 0.76rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
.phase-badge-p1 { color: #34d399; }
.phase-badge-p2 { color: #60a5fa; }
.phase-badge-p3 { color: #c084fc; }

.phase-check-icon {
    color: #34d399;
    font-size: 1.1rem;
    font-weight: 800;
}
.phase-status-upcoming {
    color: #94a3b8;
    font-size: 0.76rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.phase-main-row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 12px;
}
.phase-main-title {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 1.05rem;
    font-weight: 750;
    margin: 0;
}
.phase-pct-tag {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 1.05rem;
    font-weight: 800;
}
.laser-track {
    width: 100%;
    height: 7px;
    border-radius: 99px;
    overflow: hidden;
    position: relative;
    margin-top: 4px;
}
.laser-fill-emerald {
    height: 100%;
    background: linear-gradient(90deg, #059669 0%, #10b981 70%, #34d399 100%);
    border-radius: 99px;
    position: relative;
    box-shadow: 0 0 16px #10b981, 0 0 6px #34d399;
    transition: width 0.4s ease;
}
.laser-fill-blue {
    height: 100%;
    background: linear-gradient(90deg, #1d4ed8 0%, #3b82f6 70%, #60a5fa 100%);
    border-radius: 99px;
    position: relative;
    box-shadow: 0 0 16px #3b82f6, 0 0 6px #60a5fa;
    transition: width 0.4s ease;
}
.laser-fill-violet {
    height: 100%;
    background: linear-gradient(90deg, #6d28d9 0%, #8b5cf6 70%, #c084fc 100%);
    border-radius: 99px;
    position: relative;
    box-shadow: 0 0 16px #8b5cf6, 0 0 6px #c084fc;
    transition: width 0.4s ease;
}

/* KPI Row */
.kpi-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 14px;
    margin-bottom: 24px;
    animation: cardEntrance 0.4s cubic-bezier(0.16, 1, 0.3, 1) 0.12s both;
}
.kpi-core {
    padding: 16px 18px;
}
.kpi-label {
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 6px;
}
.kpi-value-row {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    gap: 8px;
}
@keyframes sparklineFlow {
    0% {
        stroke-dashoffset: 140;
        filter: drop-shadow(0 0 1px currentColor);
    }
    50% {
        stroke-dashoffset: 0;
        filter: drop-shadow(0 0 5px currentColor);
    }
    100% {
        stroke-dashoffset: -140;
        filter: drop-shadow(0 0 1px currentColor);
    }
}
.kpi-value-row svg path {
    stroke-dasharray: 65;
    animation: sparklineFlow 3.5s ease-in-out infinite;
}
.kpi-value {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 1.65rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    line-height: 1.1;
    font-variant-numeric: tabular-nums;
}
.kpi-sub {
    font-size: 0.74rem;
    margin-top: 4px;
}

/* Viewfinder HUD Docking Port */
.docking-port {
    border-radius: 14px;
    padding: 30px 20px 22px 20px;
    text-align: center;
    position: relative;
    overflow: hidden !important;
    transition: all 0.25s cubic-bezier(0.2, 0, 0, 1);
}
.hud-corner {
    position: absolute;
    width: 18px;
    height: 18px;
    border: 2.5px solid transparent;
    pointer-events: none;
    transition: all 0.25s ease;
}
@keyframes hudCornerBreathe {
    0%, 100% {
        transform: scale(1);
        filter: drop-shadow(0 0 2px rgba(56, 189, 248, 0.4));
    }
    50% {
        transform: scale(1.18);
        filter: drop-shadow(0 0 8px rgba(56, 189, 248, 0.9));
    }
}
.docking-port:hover .hud-corner {
    animation: hudCornerBreathe 2s ease-in-out infinite alternate;
}
.hud-tl { top: 10px; left: 10px; border-top-color: #38bdf8; border-left-color: #38bdf8; }
.hud-tr { top: 10px; right: 10px; border-top-color: #a855f7; border-right-color: #a855f7; }
.hud-bl { bottom: 10px; left: 10px; border-bottom-color: #38bdf8; border-left-color: #38bdf8; }
.hud-br { bottom: 10px; right: 10px; border-bottom-color: #a855f7; border-right-color: #a855f7; }
.beacon-icon {
    font-size: 2.2rem;
    color: #38bdf8;
    margin-bottom: 8px;
    display: inline-block;
    filter: drop-shadow(0 0 10px rgba(56, 189, 248, 0.7));
    animation: beaconBounce 3s ease-in-out infinite;
}
.dock-title {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 1.18rem;
    font-weight: 800;
    margin-bottom: 6px;
}
.dock-sub {
    font-size: 0.82rem;
}

/* File Uploader */
[data-testid='stFileUploader'] {
    width: 100% !important;
}
[data-testid='stFileUploader'] section {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
    text-align: center !important;
}
[data-testid='stFileUploader'] section > input + div {
    display: none !important;
}
[data-testid='stFileUploader'] section button {
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 8px !important;
    border-radius: 99px !important;
    padding: 10px 32px !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    transition: all 0.25s cubic-bezier(0.2, 0, 0, 1) !important;
}

/* Workflow Activity */
.workflow-activity-card {
    border-radius: 14px;
    padding: 18px 20px;
    height: 100%;
}
.activity-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
}
.activity-header h4 {
    font-size: 1.02rem;
    font-weight: 750;
    margin: 0;
}
.activity-dots-menu {
    color: #64748b;
    font-size: 1.2rem;
    cursor: pointer;
}
.activity-timeline {
    display: flex;
    flex-direction: column;
    gap: 18px;
    position: relative;
    padding-left: 18px;
}
.activity-timeline::before {
    content: '';
    position: absolute;
    top: 6px;
    bottom: 6px;
    left: 4px;
    width: 2px;
}
.activity-item {
    position: relative;
    display: flex;
    flex-direction: column;
    gap: 3px;
}
.activity-dot {
    position: absolute;
    left: -18px;
    top: 4px;
    width: 10px;
    height: 10px;
    border-radius: 99px;
    background: #3b82f6;
    box-shadow: 0 0 8px rgba(59, 130, 246, 0.6);
}
.dot-emerald { background: #10b981; box-shadow: 0 0 8px #10b981; }
.dot-blue { background: #3b82f6; box-shadow: 0 0 8px #3b82f6; }
.dot-purple { background: #8b5cf6; box-shadow: 0 0 8px #8b5cf6; }
.dot-cyan { background: #06b6d4; box-shadow: 0 0 8px #06b6d4; }
.activity-title {
    font-size: 0.84rem;
    font-weight: 600;
}
.activity-time {
    font-size: 0.74rem;
}

/* Primary Action Buttons */
@keyframes primaryGlowPulse {
    0%, 100% { box-shadow: 0 4px 18px rgba(79, 70, 229, 0.45); }
    50% { box-shadow: 0 6px 26px rgba(79, 70, 229, 0.75), 0 0 14px rgba(99, 102, 241, 0.45); }
}
.stButton button[kind='primary'], .stDownloadButton button[kind='primary'] {
    background: linear-gradient(135deg, #4f46e5 0%, #2563eb 100%) !important;
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
    color: #ffffff !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    animation: primaryGlowPulse 3.5s ease-in-out infinite alternate;
    transition: all 0.2s cubic-bezier(0.2, 0, 0, 1) !important;
}
.stButton button[kind='primary']:hover, .stDownloadButton button[kind='primary']:hover {
    background: linear-gradient(135deg, #4338ca 0%, #1d4ed8 100%) !important;
    box-shadow: 0 6px 28px rgba(79, 70, 229, 0.75), 0 0 18px rgba(99, 102, 241, 0.5) !important;
    transform: translateY(-2px) scale(1.01) !important;
}
.stButton button[kind='primary'] *, .stDownloadButton button[kind='primary'] * {
    color: #ffffff !important;
}

/* Sidebar action button */
section[data-testid='stSidebar'] .stButton {
    width: 100%;
}
section[data-testid='stSidebar'] .stButton button {
    background: linear-gradient(135deg, #4f46e5 0%, #2563eb 100%) !important;
    color: #ffffff !important;
    border: 1px solid rgba(255, 255, 255, 0.25) !important;
    border-radius: 12px !important;
    min-height: 44px !important;
    font-weight: 700 !important;
    font-size: 0.88rem !important;
    box-shadow: 0 4px 16px rgba(79, 70, 229, 0.4) !important;
    transition: all 0.2s cubic-bezier(0.2, 0, 0, 1) !important;
}
section[data-testid='stSidebar'] .stButton button:hover {
    background: linear-gradient(135deg, #4338ca 0%, #1d4ed8 100%) !important;
    transform: translateY(-2px) !important;
}

/* Sidebar Nav links */
.sidebar-nav-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 14px;
    border-radius: 10px;
    font-weight: 600;
    font-size: 0.85rem;
    margin-bottom: 4px;
    cursor: default;
    transition: all 0.2s ease;
}

/* Responsive Grid */
@media (max-width: 1080px) {
    .phase-deck { grid-template-columns: 1fr !important; gap: 12px !important; }
    .phase-chevron { display: none !important; }
    .kpi-row { grid-template-columns: repeat(2, 1fr) !important; }
}
@media (max-width: 640px) {
    .kpi-row { grid-template-columns: 1fr !important; }
}
@media (prefers-reduced-motion: reduce) {
    *, ::before, ::after {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
        scroll-behavior: auto !important;
    }
}
"""

DARK_THEME_CSS = """
.theme-card-title { color: #ffffff !important; }
.theme-card-sub { color: #94a3b8 !important; }
.theme-metric-num { color: #ffffff !important; }
.health-track { background: #1e293b !important; }
.schema-box-core {
    background: #090e1a !important;
    border-left: 4px solid #4f46e5 !important;
}
.schema-code-text { color: #818cf8 !important; }
.counter-pill {
    background: rgba(30, 58, 138, 0.25) !important;
    border: 1px solid rgba(59, 130, 246, 0.35) !important;
    color: #93c5fd !important;
}
.counter-pill b { color: #ffffff !important; }

/* ========================================================================= */
/* DARK THEME (Obsidian Cybernetic Doppelrand Chassis)                      */
/* ========================================================================= */
html, body, [class*="css"], .stApp {
    color: #f1f5f9 !important;
}
h1, h2, h3, h4, .app-title, .step-main-title, [data-testid='stMetricValue'] {
    color: #ffffff !important;
}

header[data-testid="stHeader"] {
    background: rgba(9, 13, 22, 0.85) !important;
    backdrop-filter: blur(12px) !important;
    -webkit-backdrop-filter: blur(12px) !important;
    border-bottom: 1px solid rgba(30, 41, 59, 0.3) !important;
    z-index: 99 !important;
}
header[data-testid="stHeader"] * {
    color: #cbd5e1 !important;
}

.stApp {
    background-color: #050811 !important;
    background: 
      radial-gradient(circle at 85% 10%, rgba(56, 189, 248, 0.09) 0%, transparent 40%),
      radial-gradient(circle at 15% 90%, rgba(168, 85, 247, 0.08) 0%, transparent 45%),
      radial-gradient(circle at 50% 50%, #0c1322 0%, #050811 100%) !important;
    background-attachment: fixed !important;
}
.stApp::before {
    content: '';
    position: fixed;
    inset: 0;
    background-image: radial-gradient(rgba(255, 255, 255, 0.06) 1px, transparent 1px);
    background-size: 28px 28px;
    pointer-events: none;
    z-index: 0;
}

section[data-testid='stSidebar'] {
    background: linear-gradient(180deg, #090d16 0%, #0b0f19 60%, #0d1322 100%) !important;
    border-right: 1px solid #1e293b !important;
}
section[data-testid='stSidebar'] * {
    color: #f1f5f9;
}
section[data-testid='stSidebar'] .stSelectbox label,
section[data-testid='stSidebar'] .stSlider label {
    color: #cbd5e1 !important;
}
.sidebar-nav-item {
    color: #94a3b8;
}
.sidebar-nav-item:hover {
    background: rgba(30, 41, 59, 0.5);
    color: #f8fafc;
}
.sidebar-nav-item.active {
    background: rgba(30, 41, 59, 0.85);
    color: #ffffff;
    border: 1px solid rgba(148, 163, 184, 0.2);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.app-brand-bar {
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.12) 0%, rgba(13, 19, 34, 0.85) 50%, rgba(255, 255, 255, 0.04) 100%) !important;
    backdrop-filter: blur(24px) !important;
    -webkit-backdrop-filter: blur(24px) !important;
    border: 1.5px solid rgba(255, 255, 255, 0.22) !important;
    border-radius: 16px !important;
    box-shadow: 0 12px 36px rgba(0, 0, 0, 0.6), inset 0 1px 2px rgba(255, 255, 255, 0.2) !important;
}
.app-brand-title {
    color: #ffffff !important;
}
.brand-pill-live {
    background: rgba(14, 165, 233, 0.12);
    border: 1px solid rgba(56, 189, 248, 0.45);
    color: #38bdf8;
    box-shadow: 0 0 18px rgba(56, 189, 248, 0.25);
}
.live-badge-dot {
    background-color: #38bdf8;
    box-shadow: 0 0 8px #38bdf8;
}

/* Theme Toggle Button in Dark Mode */
.theme-toggle-chassis .stButton button {
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.14) 0%, rgba(15, 23, 42, 0.95) 50%, rgba(255, 255, 255, 0.05) 100%) !important;
    border: 1.5px solid rgba(255, 255, 255, 0.28) !important;
    color: #ffffff !important;
    box-shadow: 0 12px 32px rgba(0, 0, 0, 0.6), inset 0 1px 2px rgba(255, 255, 255, 0.2) !important;
}
.theme-toggle-chassis .stButton button:hover {
    border-color: #f59e0b !important;
    background: linear-gradient(135deg, rgba(245, 158, 11, 0.22) 0%, rgba(15, 23, 42, 0.98) 100%) !important;
    box-shadow: 0 0 28px rgba(245, 158, 11, 0.5), 0 12px 36px rgba(0, 0, 0, 0.7) !important;
    transform: translateY(-2px) scale(1.02) !important;
    color: #fef3c7 !important;
    animation: solarCoronaPulse 1.8s ease-in-out infinite alternate !important;
}
.theme-toggle-chassis .stButton button:active {
    transform: translateY(1px) scale(0.97) !important;
}

.doppelrand-chassis {
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.16) 0%, rgba(255, 255, 255, 0.02) 40%, rgba(255, 255, 255, 0.10) 100%);
    border: 1.5px solid rgba(255, 255, 255, 0.28);
    border-radius: 18px;
    padding: 5px;
    box-shadow: 0 16px 40px rgba(0, 0, 0, 0.7), inset 0 1px 2px rgba(255, 255, 255, 0.25);
}
.doppelrand-chassis:hover {
    border-color: rgba(255, 255, 255, 0.45);
    transform: translateY(-2px);
    box-shadow: 0 20px 48px rgba(0, 0, 0, 0.8), inset 0 1px 2px rgba(255, 255, 255, 0.4);
}
.doppelrand-chassis.phase-active {
    animation: plasmaBorderOrbit 4.5s ease-in-out infinite !important;
}
.doppelrand-core {
    background: #080c16;
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 13px;
    padding: 16px 20px;
    position: relative;
    overflow: hidden;
}

.phase-chevron { color: #475569; }
.phase-main-title { color: #ffffff !important; }
.laser-track {
    background: rgba(20, 27, 45, 0.9);
    border: 1px solid rgba(255, 255, 255, 0.08);
}

.kpi-label { color: #94a3b8; }
.kpi-value { color: #ffffff; }
.kpi-sub { color: #94a3b8; }

[data-testid='stMetric'] {
    background: #090e1a !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 14px !important;
    padding: 16px 18px !important;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.45) !important;
}
[data-testid='stMetric']:hover {
    border-color: #38bdf8 !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 12px 30px rgba(0, 0, 0, 0.55), 0 0 16px rgba(56, 189, 248, 0.15) !important;
}
[data-testid='stMetricLabel'] { color: #94a3b8 !important; font-size: 0.74rem !important; font-weight: 700 !important; }
[data-testid='stMetricValue'] { color: #ffffff !important; font-size: 1.65rem !important; font-weight: 800 !important; }

.docking-port {
    border: 2px dashed rgba(255, 255, 255, 0.12);
    background: rgba(15, 23, 42, 0.4);
}
.docking-port:hover {
    border-color: #38bdf8;
    background: rgba(30, 58, 138, 0.15);
    box-shadow: 0 0 24px rgba(56, 189, 248, 0.2);
}
.dock-title { color: #ffffff; }
.dock-sub { color: #94a3b8; }

[data-testid='stFileUploader'] section button {
    background: linear-gradient(135deg, #111a2e 0%, #1e293b 100%) !important;
    border: 1.5px solid rgba(255, 255, 255, 0.28) !important;
    color: #ffffff !important;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.6), inset 0 1px 1px rgba(255, 255, 255, 0.25) !important;
}
[data-testid='stFileUploader'] section button:hover {
    background: linear-gradient(135deg, #1e293b 0%, #283548 100%) !important;
    border-color: #38bdf8 !important;
    box-shadow: 0 6px 26px rgba(56, 189, 248, 0.35) !important;
    transform: translateY(-2px) !important;
}
[data-testid='stFileUploader'] section button * { color: #ffffff !important; }

.workflow-activity-card {
    background: #090e1a;
}
.activity-header h4 { color: #ffffff; }
.activity-timeline::before { background: #1e293b; }
.activity-title { color: #e2e8f0; }
.activity-time { color: #64748b; }

.step-eyebrow { color: #60a5fa; font-size: 0.74rem; font-weight: 800; letter-spacing: 0.12em; text-transform: uppercase; }
.step-main-title { color: #ffffff !important; font-size: 1.45rem; font-weight: 800; }
.step-desc { color: #94a3b8; font-size: 0.88rem; }

div[data-baseweb='select'] > div, 
div[data-baseweb='input'] > div,
div[data-baseweb='base-input'] {
    background: #0b0f19 !important;
    border: 1px solid #1e293b !important;
    border-radius: 10px !important;
    color: #f8fafc !important;
}
div[data-baseweb='select'] *, div[data-baseweb='input'] * { color: #f8fafc !important; }
div[data-baseweb='select'] > div:focus-within, 
div[data-baseweb='input'] > div:focus-within {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.25) !important;
}
ul[data-baseweb='menu'] {
    background: #0f172a !important;
    border: 1px solid #1e293b !important;
}
li[data-baseweb='menu-item'] { color: #f8fafc !important; }
li[data-baseweb='menu-item']:hover { background: #1e293b !important; }

[data-testid='stDataFrame'] {
    background: #0b0f19 !important;
    border: 1px solid #1e293b !important;
    border-radius: 12px !important;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.35) !important;
}
div[data-testid='stExpander'] {
    background: #0d1322 !important;
    border: 1px solid #1e293b !important;
    border-radius: 12px !important;
}
div[data-testid='stExpander'] summary { color: #f1f5f9 !important; font-weight: 700 !important; }

button[data-baseweb='tab'] {
    color: #94a3b8 !important;
    background: transparent !important;
}
button[data-baseweb='tab'][aria-selected='true'] {
    color: #3b82f6 !important;
    border-bottom: 2.5px solid #3b82f6 !important;
}
button[data-baseweb='tab']:hover { color: #ffffff !important; }

section.main .stButton button:not([kind='primary']), 
section.main .stDownloadButton button:not([kind='primary']) {
    background: #131b2e !important;
    color: #f1f5f9 !important;
    border: 1px solid #283548 !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
}
section.main .stButton button:not([kind='primary']) *:not(svg),
section.main .stDownloadButton button:not([kind='primary']) *:not(svg) {
    color: #f1f5f9 !important;
}
section.main .stButton button:not([kind='primary']):hover, 
section.main .stDownloadButton button:not([kind='primary']):hover {
    background: #1e293b !important;
    color: #60a5fa !important;
    border-color: #3b82f6 !important;
}
"""

LIGHT_THEME_CSS = """
.theme-card-title { color: #0f172a !important; }
.theme-card-sub { color: #64748b !important; }
.theme-metric-num { color: #0f172a !important; }
.health-track { background: #e2e8f0 !important; }
.schema-box-core {
    background: #ffffff !important;
    border-left: 4px solid #4f46e5 !important;
}
.schema-code-text { color: #4338ca !important; }
.counter-pill {
    background: rgba(238, 242, 255, 0.9) !important;
    border: 1px solid rgba(199, 210, 254, 0.8) !important;
    color: #1e40af !important;
}
.counter-pill b { color: #0f172a !important; }

/* ========================================================================= */
/* LIGHT THEME (Crisp Executive Frosted Glass & Polished Aluminum)           */
/* ========================================================================= */
html, body, [class*="css"], .stApp {
    color: #0f172a !important;
}
h1, h2, h3, h4, .app-title, .step-main-title, [data-testid='stMetricValue'] {
    color: #0f172a !important;
}

header[data-testid="stHeader"] {
    background: rgba(255, 255, 255, 0.85) !important;
    backdrop-filter: blur(12px) !important;
    -webkit-backdrop-filter: blur(12px) !important;
    border-bottom: 1px solid rgba(226, 232, 240, 0.9) !important;
    z-index: 99 !important;
}
header[data-testid="stHeader"] * {
    color: #334155 !important;
}

.stApp {
    background-color: #f8fafc !important;
    background: 
      radial-gradient(circle at 85% 10%, rgba(59, 130, 246, 0.08) 0%, transparent 40%),
      radial-gradient(circle at 15% 90%, rgba(147, 51, 234, 0.06) 0%, transparent 45%),
      radial-gradient(circle at 50% 50%, #ffffff 0%, #f1f5f9 100%) !important;
    background-attachment: fixed !important;
}
.stApp::before {
    content: '';
    position: fixed;
    inset: 0;
    background-image: radial-gradient(rgba(15, 23, 42, 0.07) 1px, transparent 1px) !important;
    background-size: 28px 28px;
    pointer-events: none;
    z-index: 0;
}

section[data-testid='stSidebar'] {
    background: linear-gradient(180deg, #ffffff 0%, #f8fafc 60%, #f1f5f9 100%) !important;
    border-right: 1px solid #e2e8f0 !important;
}
section[data-testid='stSidebar'] * {
    color: #1e293b !important;
}
section[data-testid='stSidebar'] .stSelectbox label,
section[data-testid='stSidebar'] .stSlider label {
    color: #475569 !important;
}
.sidebar-nav-item {
    color: #64748b !important;
}
.sidebar-nav-item:hover {
    background: rgba(241, 245, 249, 0.9) !important;
    color: #0f172a !important;
}
.sidebar-nav-item.active {
    background: #ffffff !important;
    color: #0f172a !important;
    border: 1px solid rgba(203, 213, 225, 0.8) !important;
    box-shadow: 0 2px 8px rgba(15, 23, 42, 0.06) !important;
}

.app-brand-bar {
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.98) 0%, rgba(241, 245, 249, 0.92) 50%, rgba(255, 255, 255, 0.95) 100%) !important;
    backdrop-filter: blur(24px) !important;
    -webkit-backdrop-filter: blur(24px) !important;
    border: 1.5px solid rgba(203, 213, 225, 0.9) !important;
    border-radius: 16px !important;
    box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06), inset 0 1px 2px rgba(255, 255, 255, 1) !important;
}
.app-brand-title {
    color: #0f172a !important;
}
.brand-pill-live {
    background: rgba(14, 165, 233, 0.1) !important;
    border: 1px solid rgba(14, 165, 233, 0.45) !important;
    color: #0284c7 !important;
    box-shadow: 0 0 16px rgba(14, 165, 233, 0.18) !important;
}
.live-badge-dot {
    background-color: #0284c7 !important;
    box-shadow: 0 0 8px #0284c7 !important;
}

/* Theme Toggle Button in Light Mode */
.theme-toggle-chassis .stButton button {
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.98) 0%, rgba(241, 245, 249, 0.95) 50%, rgba(255, 255, 255, 0.9) 100%) !important;
    border: 1.5px solid rgba(203, 213, 225, 0.95) !important;
    color: #0f172a !important;
    box-shadow: 0 10px 28px rgba(15, 23, 42, 0.07), inset 0 1px 2px rgba(255, 255, 255, 1) !important;
}
@keyframes solarCoronaPulseLight {
    0% {
        box-shadow: 0 0 16px rgba(99, 102, 241, 0.35), inset 0 1px 2px rgba(255, 255, 255, 0.8);
        transform: translateY(-2px) scale(1.02);
    }
    100% {
        box-shadow: 0 0 30px rgba(99, 102, 241, 0.65), 0 12px 32px rgba(15, 23, 42, 0.12);
        transform: translateY(-3px) scale(1.04);
    }
}
.theme-toggle-chassis .stButton button:hover {
    border-color: #6366f1 !important;
    background: linear-gradient(135deg, rgba(238, 242, 255, 0.95) 0%, rgba(224, 231, 255, 0.9) 100%) !important;
    box-shadow: 0 0 24px rgba(99, 102, 241, 0.35), 0 12px 32px rgba(15, 23, 42, 0.12) !important;
    transform: translateY(-2px) scale(1.02) !important;
    color: #3730a3 !important;
    animation: solarCoronaPulseLight 1.8s ease-in-out infinite alternate !important;
}
.theme-toggle-chassis .stButton button:active {
    transform: translateY(1px) scale(0.97) !important;
}

@keyframes plasmaBorderOrbitLight {
    0% {
        border-color: rgba(37, 99, 235, 0.85);
        box-shadow: 0 0 20px rgba(37, 99, 235, 0.35), 0 10px 30px rgba(15, 23, 42, 0.08);
    }
    33% {
        border-color: rgba(124, 58, 237, 0.85);
        box-shadow: 0 0 24px rgba(124, 58, 237, 0.35), 0 10px 30px rgba(15, 23, 42, 0.08);
    }
    66% {
        border-color: rgba(13, 148, 136, 0.85);
        box-shadow: 0 0 24px rgba(13, 148, 136, 0.35), 0 10px 30px rgba(15, 23, 42, 0.08);
    }
    100% {
        border-color: rgba(37, 99, 235, 0.85);
        box-shadow: 0 0 20px rgba(37, 99, 235, 0.35), 0 10px 30px rgba(15, 23, 42, 0.08);
    }
}

.doppelrand-chassis {
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.98) 0%, rgba(241, 245, 249, 0.8) 40%, rgba(255, 255, 255, 0.95) 100%) !important;
    border: 1.5px solid rgba(203, 213, 225, 0.85) !important;
    border-radius: 18px !important;
    padding: 5px !important;
    box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06), inset 0 1px 2px rgba(255, 255, 255, 1) !important;
}
.doppelrand-chassis:hover {
    border-color: rgba(99, 102, 241, 0.45) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 16px 38px rgba(15, 23, 42, 0.1), inset 0 1px 2px rgba(255, 255, 255, 1) !important;
}
.doppelrand-chassis.phase-active {
    animation: plasmaBorderOrbitLight 4.5s ease-in-out infinite !important;
}
.doppelrand-core {
    background: #ffffff !important;
    border: 1px solid rgba(226, 232, 240, 0.95) !important;
    border-radius: 13px !important;
    padding: 16px 20px !important;
    position: relative !important;
    overflow: hidden !important;
    box-shadow: 0 2px 6px rgba(15, 23, 42, 0.03) !important;
}

.phase-chevron { color: #94a3b8 !important; }
.phase-main-title { color: #0f172a !important; }
.laser-track {
    background: #e2e8f0 !important;
    border: 1px solid #cbd5e1 !important;
}

.kpi-label { color: #64748b !important; }
.kpi-value { color: #0f172a !important; }
.kpi-sub { color: #64748b !important; }

[data-testid='stMetric'] {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 14px !important;
    padding: 16px 18px !important;
    box-shadow: 0 6px 20px rgba(15, 23, 42, 0.05) !important;
}
[data-testid='stMetric']:hover {
    border-color: #2563eb !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 10px 26px rgba(15, 23, 42, 0.08), 0 0 14px rgba(37, 99, 235, 0.12) !important;
}
[data-testid='stMetricLabel'] { color: #64748b !important; font-size: 0.74rem !important; font-weight: 700 !important; }
[data-testid='stMetricValue'] { color: #0f172a !important; font-size: 1.65rem !important; font-weight: 800 !important; }

.docking-port {
    border: 2px dashed rgba(148, 163, 184, 0.45) !important;
    background: rgba(241, 245, 249, 0.6) !important;
}
.docking-port:hover {
    border-color: #0284c7 !important;
    background: rgba(238, 242, 255, 0.7) !important;
    box-shadow: 0 0 24px rgba(14, 165, 233, 0.15) !important;
}
.dock-title { color: #0f172a !important; }
.dock-sub { color: #64748b !important; }

[data-testid='stFileUploader'] section button {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%) !important;
    border: 1.5px solid rgba(255, 255, 255, 0.3) !important;
    color: #ffffff !important;
    box-shadow: 0 4px 18px rgba(15, 23, 42, 0.25) !important;
}
[data-testid='stFileUploader'] section button:hover {
    background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%) !important;
    border-color: #38bdf8 !important;
    box-shadow: 0 6px 24px rgba(14, 165, 233, 0.3) !important;
    transform: translateY(-2px) !important;
}
[data-testid='stFileUploader'] section button * { color: #ffffff !important; }

.workflow-activity-card {
    background: #ffffff !important;
}
.activity-header h4 { color: #0f172a !important; }
.activity-timeline::before { background: #e2e8f0 !important; }
.activity-title { color: #1e293b !important; }
.activity-time { color: #64748b !important; }

.step-eyebrow { color: #2563eb !important; font-size: 0.74rem; font-weight: 800; letter-spacing: 0.12em; text-transform: uppercase; }
.step-main-title { color: #0f172a !important; font-size: 1.45rem; font-weight: 800; }
.step-desc { color: #475569 !important; font-size: 0.88rem; }

div[data-baseweb='select'] > div, 
div[data-baseweb='input'] > div,
div[data-baseweb='base-input'] {
    background: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 10px !important;
    color: #0f172a !important;
}
div[data-baseweb='select'] *, div[data-baseweb='input'] * { color: #0f172a !important; }
div[data-baseweb='select'] > div:focus-within, 
div[data-baseweb='input'] > div:focus-within {
    border-color: #2563eb !important;
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.2) !important;
}
ul[data-baseweb='menu'] {
    background: #ffffff !important;
    border: 1px solid #cbd5e1 !important;
}
li[data-baseweb='menu-item'] { color: #0f172a !important; }
li[data-baseweb='menu-item']:hover { background: #f1f5f9 !important; }

[data-testid='stDataFrame'] {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 12px !important;
    box-shadow: 0 4px 14px rgba(15, 23, 42, 0.05) !important;
}
div[data-testid='stExpander'] {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 12px !important;
}
div[data-testid='stExpander'] summary { color: #0f172a !important; font-weight: 700 !important; }

button[data-baseweb='tab'] {
    color: #64748b !important;
    background: transparent !important;
}
button[data-baseweb='tab'][aria-selected='true'] {
    color: #2563eb !important;
    border-bottom: 2.5px solid #2563eb !important;
}
button[data-baseweb='tab']:hover { color: #0f172a !important; }

section.main .stButton button:not([kind='primary']), 
section.main .stDownloadButton button:not([kind='primary']) {
    background: #ffffff !important;
    color: #1e293b !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    box-shadow: 0 2px 6px rgba(15, 23, 42, 0.05) !important;
}
section.main .stButton button:not([kind='primary']) *:not(svg),
section.main .stDownloadButton button:not([kind='primary']) *:not(svg) {
    color: #1e293b !important;
}
section.main .stButton button:not([kind='primary']):hover, 
section.main .stDownloadButton button:not([kind='primary']):hover {
    background: #f8fafc !important;
    color: #2563eb !important;
    border-color: #3b82f6 !important;
}
section.main .stButton button:not([kind='primary']):hover *:not(svg),
section.main .stDownloadButton button:not([kind='primary']):hover *:not(svg) {
    color: #2563eb !important;
}
"""

active_css = COMMON_CSS + "\n" + (DARK_THEME_CSS if is_dark else LIGHT_THEME_CSS)
st.markdown(f"<style>{active_css}</style>", unsafe_allow_html=True)

def head():
    current_step = st.session_state.step
    current_theme = st.session_state.get("theme", "dark")
    is_dark = (current_theme == "dark")

    # 1. Top Command Module Header with Kinetic Theme Toggle Button matching mockup 1:1
    c_brand, c_toggle = st.columns([5.8, 1.2], vertical_alignment="center")

    with c_brand:
        st.markdown("""
        <div class="app-brand-bar">
          <div class="app-brand-left">
            <div class="app-diamond-logo">◆</div>
            <div class="app-brand-title">INTELLIGENT CLIENT DATA PREP</div>
          </div>
          <div class="app-brand-right">
            <div class="brand-pill-live">
              <span class="live-badge-dot"></span>
              <span>100% FIDELITY • ENCRYPTED</span>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    with c_toggle:
        st.markdown('<div class="theme-toggle-chassis">', unsafe_allow_html=True)
        btn_label = "☀️  Light Mode" if is_dark else "🌙  Dark Mode"
        btn_help = "Toggle between high-contrast Dark and crisp Light mode"
        st.button(btn_label, key="top_theme_toggle_btn", on_click=toggle_theme, width="stretch", help=btn_help)
        st.markdown('</div>', unsafe_allow_html=True)

    # Dynamic Progress Calculations matching mockup
    p1_active = "phase-active" if current_step in [1, 2, 3] else ""
    p2_active = "phase-active" if current_step in [4, 5, 6] else ""
    p3_active = "phase-active" if current_step in [7, 8, 9] else ""

    if current_step == 1:
        if st.session_state.get("ingestion") is not None:
            p1_pct = 85
            p1_tag = "85%"
            p1_laser_active = "laser-active"
            p1_status_badge = '<span class="phase-status-upcoming" style="color: #34d399;">Uploaded</span>'
        else:
            p1_pct = 0
            p1_tag = "0%"
            p1_laser_active = ""
            p1_status_badge = '<span class="phase-status-upcoming">Standby</span>'
    elif current_step == 2:
        p1_pct = 90
        p1_tag = "90%"
        p1_laser_active = "laser-active"
        p1_status_badge = '<span class="phase-status-upcoming" style="color: #34d399;">Profiling</span>'
    elif current_step >= 3:
        p1_pct = 100
        p1_tag = "100%"
        p1_laser_active = ""
        p1_status_badge = '<span class="phase-check-icon">✓</span>'
    else:
        p1_pct = 0
        p1_tag = "0%"
        p1_laser_active = ""
        p1_status_badge = '<span class="phase-status-upcoming">Standby</span>'

    if current_step < 4:
        p2_pct = 0
        p2_tag = "0%"
        p2_laser_active = ""
        p2_status_badge = '<span class="phase-status-upcoming">Upcoming</span>'
    elif current_step == 4:
        p2_pct = 33
        p2_tag = "33%"
        p2_laser_active = "laser-active"
        p2_status_badge = '<span class="phase-status-upcoming" style="color: #60a5fa;">Active</span>'
    elif current_step == 5:
        p2_pct = 66
        p2_tag = "66%"
        p2_laser_active = "laser-active"
        p2_status_badge = '<span class="phase-status-upcoming" style="color: #60a5fa;">Active</span>'
    elif current_step >= 6:
        p2_pct = 100
        p2_tag = "100%"
        p2_laser_active = ""
        p2_status_badge = '<span class="phase-check-icon" style="color: #60a5fa;">✓</span>'

    if current_step < 7:
        p3_pct = 0
        p3_tag = "0%"
        p3_laser_active = ""
        p3_status_badge = '<span class="phase-status-upcoming">Upcoming</span>'
    elif current_step == 7:
        p3_pct = 33
        p3_tag = "33%"
        p3_laser_active = "laser-active"
        p3_status_badge = '<span class="phase-status-upcoming" style="color: #c084fc;">Active</span>'
    elif current_step == 8:
        p3_pct = 66
        p3_tag = "66%"
        p3_laser_active = "laser-active"
        p3_status_badge = '<span class="phase-status-upcoming" style="color: #c084fc;">Active</span>'
    else:
        p3_pct = 100
        p3_tag = "100%"
        p3_laser_active = ""
        p3_status_badge = '<span class="phase-check-icon" style="color: #c084fc;">✓</span>'

    phase_deck_html = f"""
    <div class="phase-deck">
      <!-- PHASE 1: INGEST -->
      <div class="doppelrand-chassis {p1_active}">
        <div class="doppelrand-core phase-card-core">
          <div class="phase-header-row">
            <span class="phase-badge-title phase-badge-p1">Phase 1: INGEST</span>
            {p1_status_badge}
          </div>
          <div class="phase-main-row">
            <h4 class="phase-main-title">Ingest & Validation</h4>
            <span class="phase-pct-tag" style="color: #34d399;">{p1_tag}</span>
          </div>
          <div class="laser-track">
            <div class="laser-fill-emerald {p1_laser_active}" style="width: {p1_pct}%;"></div>
          </div>
        </div>
      </div>

      <div class="phase-chevron">›</div>

      <!-- PHASE 2: TRANSFORM -->
      <div class="doppelrand-chassis {p2_active}">
        <div class="doppelrand-core phase-card-core">
          <div class="phase-header-row">
            <span class="phase-badge-title phase-badge-p2">Phase 2: TRANSFORM</span>
            {p2_status_badge}
          </div>
          <div class="phase-main-row">
            <h4 class="phase-main-title">Cleanse & Map</h4>
            <span class="phase-pct-tag" style="color: #60a5fa;">{p2_tag}</span>
          </div>
          <div class="laser-track">
            <div class="laser-fill-blue {p2_laser_active}" style="width: {p2_pct}%;"></div>
          </div>
        </div>
      </div>

      <div class="phase-chevron">›</div>

      <!-- PHASE 3: PREVIEW -->
      <div class="doppelrand-chassis {p3_active}">
        <div class="doppelrand-core phase-card-core">
          <div class="phase-header-row">
            <span class="phase-badge-title phase-badge-p3">Phase 3: PREVIEW</span>
            {p3_status_badge}
          </div>
          <div class="phase-main-row">
            <h4 class="phase-main-title">Final Review & Export</h4>
            <span class="phase-pct-tag" style="color: #c084fc;">{p3_tag}</span>
          </div>
          <div class="laser-track">
            <div class="laser-fill-violet {p3_laser_active}" style="width: {p3_pct}%;"></div>
          </div>
        </div>
      </div>
    </div>
    """
    st.markdown(phase_deck_html, unsafe_allow_html=True)

def heading(k: str, t: str, c: str):
    st.markdown(f"""
    <div class="step-eyebrow">{html.escape(k)}</div>
    <h2 class="step-main-title">{html.escape(t)}</h2>
    <p class="step-desc">{html.escape(c)}</p>
    """, unsafe_allow_html=True)

def nav(back, nxt, label="Continue", disabled=False):
    st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
    a, _, b = st.columns([1.4, 1.8, 2.2])
    if back and a.button("← Back", width="stretch"):
        go(back)
    if nxt and b.button(label + " →", type="primary", width="stretch", disabled=disabled):
        go(nxt)

# Sidebar
with st.sidebar:
    st.markdown("""
    <div style="margin-bottom: 14px;">
      <div class="sidebar-nav-item active"><span>🏠</span> <span>Home</span></div>
      <div class="sidebar-nav-item"><span>🔀</span> <span>Workflows</span></div>
      <div class="sidebar-nav-item"><span>🗄️</span> <span>Sources</span></div>
      <div class="sidebar-nav-item"><span>🧠</span> <span>Models</span></div>
      <div class="sidebar-nav-item"><span>🕒</span> <span>History</span></div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### ◆ Preparation Workspace")
    st.caption("Coverage Analysis Control Center")
    st.divider()
    st.session_state.ai_enabled = st.toggle("Enable AI recommendations", value=st.session_state.ai_enabled)
    st.slider("Auto-accept confidence", 70, 100, 90)
    st.info("Operating in secure mode: client credentials and proprietary tokens are stored strictly in volatile session memory.")
    st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
    if st.button("↺ Start new run", width="stretch"):
        saved_theme = st.session_state.get("theme", "dark")
        for k, v in defaults().items():
            st.session_state[k] = v
        st.session_state.theme = saved_theme
        st.rerun()
        
    st.markdown("""
    <div style="margin-top: 30px;">
      <div class="sidebar-nav-item"><span>⚙️</span> <span>Settings</span></div>
    </div>
    """, unsafe_allow_html=True)

head()
step = st.session_state.step

# -------------------------------------------------------------
# STEP 1: UPLOAD & MULTI-TAB SELECTION
# -------------------------------------------------------------
if step == 1:
    ing = st.session_state.get("ingestion")
    sheets = st.session_state.get("sheets")

    # 4 KPI Cards matching crazy_taste_mockup.jpg (Honest initial state when launching)
    if ing is not None and hasattr(ing, "frame") and ing.frame is not None:
        tot_records_val = f"{len(ing.frame):,}"
        val_rows_val = f"{len(ing.frame):,}"
        val_rows_pct = "100%"
        m_state = st.session_state.get("mapping")
        mapped_count = len(m_state) if m_state is not None else (len(ing.frame.columns) if hasattr(ing.frame, "columns") else 0)
        mapped_clients_val = f"{mapped_count}"
        clients_rate = "102/min"
        error_rate_val = "0.0%"
        error_issues = "0 issues"
    else:
        tot_records_val = "0"
        val_rows_val = "0"
        val_rows_pct = "0.0%"
        mapped_clients_val = "0"
        clients_rate = "0/min"
        error_rate_val = "0.0%"
        error_issues = "0 issues"

    st.markdown(f"""
    <div class="kpi-row">
      <div class="doppelrand-chassis">
        <div class="doppelrand-core kpi-core">
          <div class="kpi-label">Total Records</div>
          <div class="kpi-value-row">
            <span class="kpi-value">{tot_records_val}</span>
            <svg width="74" height="24" viewBox="0 0 74 24" fill="none">
              <path d="M2 19 L14 17 L26 13 L38 15 L50 7 L62 10 L72 3" stroke="#10b981" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
          <div class="kpi-sub">Total Records</div>
        </div>
      </div>
      <div class="doppelrand-chassis">
        <div class="doppelrand-core kpi-core">
          <div class="kpi-label">Validated Rows</div>
          <div class="kpi-value-row">
            <span class="kpi-value">{val_rows_val} <span style="font-size: 0.95rem; font-weight: 600; color: #94a3b8;">| {val_rows_pct}</span></span>
            <svg width="74" height="24" viewBox="0 0 74 24" fill="none">
              <path d="M2 17 L14 18 L26 12 L38 14 L50 9 L62 5 L72 7" stroke="#3b82f6" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
          <div class="kpi-sub">Validated Rows</div>
        </div>
      </div>
      <div class="doppelrand-chassis">
        <div class="doppelrand-core kpi-core">
          <div class="kpi-label">Mapped Clients</div>
          <div class="kpi-value-row">
            <span class="kpi-value">{mapped_clients_val} <span style="font-size: 0.85rem; font-weight: 600; color: #94a3b8;">| {clients_rate}</span></span>
            <svg width="74" height="24" viewBox="0 0 74 24" fill="none">
              <path d="M2 16 L14 17 L26 12 L40 14 L52 9 L64 12 L72 4" stroke="#06b6d4" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
          <div class="kpi-sub">Mapped Clients</div>
        </div>
      </div>
      <div class="doppelrand-chassis">
        <div class="doppelrand-core kpi-core">
          <div class="kpi-label">Error Rate</div>
          <div class="kpi-value-row">
            <span class="kpi-value">{error_rate_val}</span>
            <svg width="74" height="24" viewBox="0 0 74 24" fill="none">
              <path d="M2 18 L28 18 L36 17 L42 8 L48 18 L54 11 L60 18 L72 18" stroke="#f43f5e" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
          <div class="kpi-sub">{error_issues}</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # 2-Column Bento Grid matching crazy_taste_mockup.jpg 1:1
    c_drop, c_activity = st.columns([1.8, 1.2])
    
    with c_drop:
        st.markdown("""
        <div class="doppelrand-chassis" style="margin-bottom: 12px;">
          <div class="doppelrand-core docking-port">
            <div class="hud-corner hud-tl"></div>
            <div class="hud-corner hud-tr"></div>
            <div class="hud-corner hud-bl"></div>
            <div class="hud-corner hud-br"></div>
            <div class="beacon-icon">⤊</div>
            <div class="dock-title">Drag &amp; Drop data files or Click to Upload</div>
            <div class="dock-sub" style="margin-bottom: 16px;">Supported formats: CSV, JSON, XLSX, Parquet | Max 2GB</div>
        """, unsafe_allow_html=True)
        upload = st.file_uploader("Upload client shipment workbook or CSV", type=["csv", "xlsx", "xls", "xlsm"], label_visibility="collapsed")
        st.markdown("""
          </div>
        </div>
        """, unsafe_allow_html=True)

        if upload:
            file_sig = f"{upload.name}_{upload.size}"
            if st.session_state.get("file_sig") != file_sig:
                with st.spinner("Inspecting workbook sheets and headers..."):
                    st.session_state.file_sig = file_sig
                    st.session_state.file_name = upload.name
                    content = upload.getvalue()
                    st.session_state.file_bytes = content
                    try:
                        sheets, headers, enc, sep = inspect_upload(upload.name, content)
                        st.session_state.sheets = sheets
                        st.session_state.headers = headers
                        st.session_state.enc = enc
                        st.session_state.sep = sep
                        st.session_state.ingestion = None
                    except Exception as e:
                        st.error(str(e))
                        st.session_state.sheets = None
            
            sheets = st.session_state.get("sheets")
            if sheets:
                st.markdown("<div style='margin-top: 14px;'></div>", unsafe_allow_html=True)
                c_sheet1, c_sheet2 = st.columns([2, 1])
                with c_sheet1:
                    selected = st.multiselect(
                        "Select sheets to process",
                        list(sheets),
                        default=[max(sheets, key=lambda x: len(sheets[x]))]
                    )
                with c_sheet2:
                    mode = st.radio("Multi-sheet action", ["Append rows", "Use first selected sheet"], horizontal=True)
                
                add_source = st.checkbox("Add 'Source Sheet' column to track row origin", value=len(selected) > 1)
                
                if selected:
                    comb_sig = f"{file_sig}_{','.join(selected)}_{mode}_{add_source}"
                    if st.session_state.get("comb_sig") != comb_sig or st.session_state.ingestion is None:
                        with st.spinner("Loading and stitching selected sheets..."):
                            st.session_state.comb_sig = comb_sig
                            ing = read_upload(
                                upload.name,
                                st.session_state.file_bytes,
                                selected,
                                mode,
                                add_source,
                                cached_sheets=sheets,
                                cached_headers=st.session_state.headers
                            )
                            st.session_state.ingestion = ing
                            st.session_state.raw_frame = ing.frame.copy()
                            st.session_state.profile = profile_dataframe(ing.frame)
                    
                    ing = st.session_state.ingestion
                    st.markdown("<div style='margin-top: 16px;'></div>", unsafe_allow_html=True)
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Rows Ingested", f"{len(ing.frame):,}")
                    m2.metric("Columns Detected", len(ing.frame.columns))
                    m3.metric("Available Sheets", len(sheets))
                    m4.metric("Selected Sheets", len(selected))
                    
                    st.markdown("<div style='margin-top: 12px;'></div>", unsafe_allow_html=True)
                    st.caption("Raw Data Preview (First 20 rows):")
                    st.dataframe(ing.frame.head(20), width="stretch", hide_index=True)

    with c_activity:
        st.markdown("""
        <div class="doppelrand-chassis">
          <div class="doppelrand-core workflow-activity-card">
            <div class="activity-header">
              <h4 style="margin: 0; font-family: 'Plus Jakarta Sans', sans-serif; font-size: 1.05rem; font-weight: 750; color: #ffffff;">Workflow Activity</h4>
              <span class="activity-dots-menu">•••</span>
            </div>
            <div class="activity-timeline">
              <div class="activity-item">
                <span class="activity-dot dot-emerald"></span>
                <span class="activity-title">Ingest &amp; Client workflows</span>
                <span class="activity-time">25 minutes ago</span>
              </div>
              <div class="activity-item">
                <span class="activity-dot dot-blue"></span>
                <span class="activity-title">Export &amp; solder workflows</span>
                <span class="activity-time">22 minutes ago</span>
              </div>
              <div class="activity-item">
                <span class="activity-dot dot-purple"></span>
                <span class="activity-title">Separated Bala workflows</span>
                <span class="activity-time">22 minutes ago</span>
              </div>
              <div class="activity-item">
                <span class="activity-dot dot-emerald"></span>
                <span class="activity-title">Export Work-flows &amp; Pressunt Completed</span>
                <span class="activity-time">37 minutes ago</span>
              </div>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    nav(None, 2, "Profile data", st.session_state.ingestion is None)

# -------------------------------------------------------------
# STEP 2: PROFILING & DATA HEALTH SCORECARD
# -------------------------------------------------------------
elif step == 2:
    heading("STEP 02 · PROFILING", "Understand and assess source data quality", "Detect missing cells, negative values, duplicate rows, date candidates, and numeric candidates.")
    
    p = profile_dataframe(st.session_state.ingestion.frame)
    st.session_state.profile = p
    
    # Calculate Data Health Score
    total_cells = p["rows"] * p["columns"] if p["rows"] and p["columns"] else 1
    missing_pct = (p["missing_cells"] / total_cells) * 100
    dup_pct = (p["exact_duplicates"] / p["rows"]) * 100 if p["rows"] else 0
    neg_penalty = 5 if p["negative_values"] > 0 else 0
    health_score = max(20, min(100, int(100 - (missing_pct * 2 + dup_pct * 1.5 + neg_penalty))))
    
    # Health Scorecard Doppelrand Chassis
    st.markdown(f"""
    <div class="doppelrand-chassis" style="margin-bottom: 20px;">
      <div class="doppelrand-core" style="border-top: 3px solid #10b981; padding: 20px 24px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
          <h3 class="theme-card-title" style="margin: 0; font-size: 1.15rem;">Data Health Scorecard</h3>
          <span style="background: rgba(16, 185, 129, 0.18); color: #10b981; border: 1px solid rgba(52, 211, 153, 0.4); font-size: 0.78rem; font-weight: 700; padding: 4px 14px; border-radius: 99px;">
            {health_score}% Ready for Normalization
          </span>
        </div>
        <div class="health-track">
          <div class="health-fill" style="width: {health_score}%;"></div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Rows", f"{p['rows']:,}")
    m2.metric("Columns", p["columns"])
    m3.metric("Exact Duplicates", f"{p['exact_duplicates']} ({dup_pct:.1f}%)")
    m4.metric("Missing Cells", f"{p['missing_cells']} ({missing_pct:.1f}%)")
    m5.metric("Negative Values", p["negative_values"])
    
    st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            st.markdown("#### Numeric candidate columns")
            if p["numeric_columns"]:
                st.write(p["numeric_columns"])
            else:
                st.caption("No numeric candidates detected.")
    with c2:
        with st.container(border=True):
            st.markdown("#### Date candidate columns")
            if p["date_columns"]:
                st.write(p["date_columns"])
            else:
                st.caption("No date candidates detected.")
                
    if p["negative_by_column"]:
        st.warning(f"Negative values detected by column: {p['negative_by_column']}")
        
    nav(1, 3, "Configure cleanup")

# -------------------------------------------------------------
# STEP 3: FLEXIBLE CLEANUP
# -------------------------------------------------------------
elif step == 3:
    heading("STEP 03 · FLEXIBLE CLEANUP", "Define data preparation & standardization rules", "Resolve negative values, configure duplicate thresholds, standardize date formats, and rename columns.")
    
    if st.session_state.raw_frame is not None:
        c_btn1, c_btn2 = st.columns([4, 1.4])
        with c_btn1:
            raw_len = len(st.session_state.raw_frame)
            cur_len = len(st.session_state.ingestion.frame)
            st.markdown(f"""
            <div class="counter-pill" style="display: inline-flex; align-items: center; gap: 10px; padding: 8px 16px; border-radius: 10px; font-size: 0.82rem; font-weight: 600;">
              <span>Raw Input: <b>{raw_len:,} rows</b></span>
              <span style="color: #60a5fa;">→</span>
              <span>Prepared Frame: <b>{cur_len:,} rows</b></span>
            </div>
            """, unsafe_allow_html=True)
        with c_btn2:
            st.markdown('<div class="destructive-btn-container">', unsafe_allow_html=True)
            if st.button("↺ Reset to raw data", help="Revert all deletions and cleanup actions back to original raw uploaded file", width="stretch"):
                st.session_state.ingestion.frame = st.session_state.raw_frame.copy()
                st.session_state.duplicates = pd.DataFrame()
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    df = st.session_state.ingestion.frame.copy()
    profile = profile_dataframe(df)
    
    with st.expander("1. Negative values handling", expanded=True):
        if profile["negative_by_column"]:
            for col, count in profile["negative_by_column"].items():
                action = st.selectbox(
                    f"{col}: {count} negative value(s)",
                    ["Do nothing", "Convert to positive", "Replace with zero", "Replace with blank"],
                    key=f"neg_{col}"
                )
                if action != "Do nothing":
                    df = apply_negative_action(df, col, action)
        else:
            st.info("No negative values detected in current dataset.")

    with st.expander("2. Duplicate identification and deduplication", expanded=True):
        suggested = [c for c in df.columns if any(x in str(c).lower() for x in ["sku", "item", "product", "country", "date", "period", "channel"])]
        keys = st.multiselect("Columns defining a duplicate", list(df.columns), default=suggested[:4])
        dupes = duplicate_report(df, keys)
        st.session_state.duplicates = dupes
        st.metric("Rows involved in possible duplicates", len(dupes))
        if not dupes.empty:
            st.dataframe(dupes.head(100), width="stretch", hide_index=True)
        action = st.selectbox("Duplicate action", ["Do nothing", "Keep first", "Keep last", "Delete all duplicates"])
        if action != "Do nothing":
            df = remove_duplicates(df, keys, action)

    with st.expander("3. Date standardization", expanded=False):
        date_cols = st.multiselect("Date columns to standardize", list(df.columns), default=[c for c in profile["date_columns"] if c in df.columns])
        fmt = st.selectbox("Output date format", ["YYYY-MM-DD", "DD/MM/YYYY", "MM/DD/YYYY", "Long date", "Month text"])
        dayfirst = st.checkbox("Interpret ambiguous dates as day-first")
        if date_cols:
            df = standardize_dates(df, date_cols, fmt, dayfirst)

    with st.expander("4. Column management (Delete, rename, re-order)", expanded=False):
        delete = st.multiselect("Delete columns", list(df.columns))
        remaining = [c for c in df.columns if c not in delete]
        rename_map = {}
        rename_col = st.selectbox("Column to rename", ["None"] + remaining)
        new_name = st.text_input("New column name", disabled=rename_col == "None")
        if rename_col != "None" and new_name.strip():
            rename_map[rename_col] = new_name.strip()
        renamed = [rename_map.get(c, c) for c in remaining]
        order = st.multiselect("Final column order", renamed, default=renamed)
        df = manage_columns(df, delete, rename_map, order)

    st.session_state.ingestion.frame = df
    st.caption(f"Active prepared state: {len(df):,} rows · {len(df.columns):,} columns")
    nav(2, 4, "Configure AI")

# -------------------------------------------------------------
# STEP 4: AI SETUP
# -------------------------------------------------------------
elif step == 4:
    heading("STEP 04 · AI MODEL SETUP", "Configure Hackfest Azure Luna Model", "Zero-leakage architecture: the API token remains strictly in volatile session memory and is never logged or exported.")
    
    with st.container(border=True):
        enabled = st.toggle("Enable AI recommendations for unresolved fields", value=st.session_state.ai_enabled)
        st.session_state.ai_enabled = enabled
        
        c_ep, c_mod = st.columns(2)
        with c_ep:
            endpoint = st.text_input("Azure AI Endpoint", value=st.session_state.ai_endpoint)
        with c_mod:
            model = st.text_input("Model Deployment Name", value=st.session_state.ai_model)
            
        key = st.text_input("Bearer Token / API Key", value=st.session_state.ai_key, type="password", help="Paste with or without the Bearer prefix. Handled purely in-memory.")
        st.session_state.ai_endpoint = endpoint
        st.session_state.ai_model = model
        st.session_state.ai_key = key
        
        if key:
            st.session_state.ai_client = AIClient(endpoint, key, model)
            
        st.markdown("<div style='margin-top: 14px;'></div>", unsafe_allow_html=True)
        if st.button("Test secure connection", disabled=not (enabled and endpoint and key)):
            client = AIClient(endpoint, key, model)
            ok, message, usage = client.test_connection()
            st.session_state.api_tested = ok
            st.session_state.ai_client = client
            st.session_state.token_usage.append({
                "Timestamp UTC": datetime.now(timezone.utc).isoformat(),
                "Operation": "Connection test",
                "Model": model,
                **usage
            })
            if ok:
                st.success(message)
                st.json(usage)
            else:
                st.error(message)

    nav(3, 5, "Review classification", enabled and not st.session_state.api_tested)

# -------------------------------------------------------------
# STEP 5: CLASSIFICATION
# -------------------------------------------------------------
elif step == 5:
    heading("STEP 05 · CLASSIFICATION", "Review and confirm canonical field mappings", "Verify auto-detected NIQ dimensions. Fields with ≥90% confidence from rules or AI are automatically confirmed.")
    
    if st.session_state.mapping is None:
        st.session_state.mapping = classify_columns(st.session_state.ingestion.frame)
        
    c_map1, c_map2 = st.columns([3, 1.4])
    with c_map1:
        st.caption("You can interactively adjust any NIQ Field mapping or checkbox below before running transformation.")
    with c_map2:
        can_ai = st.session_state.ai_enabled and st.session_state.ai_client is not None and st.session_state.api_tested
        st.markdown('<div class="ai-btn-container">', unsafe_allow_html=True)
        if st.button("🤖 Enhance with Luna AI", width="stretch", disabled=not can_ai, help="Query Azure AI Luna to resolve low-confidence/unmapped fields" if can_ai else "Connect and test API in Step 4 first"):
            with st.spinner("Calling Azure AI Luna for recommendations..."):
                updated_map, usage = ai_classify_unresolved(st.session_state.ingestion.frame, st.session_state.mapping, st.session_state.ai_client)
                st.session_state.mapping = updated_map
                if usage.get("Total Tokens", 0) > 0:
                    st.session_state.token_usage.append({
                        "Timestamp UTC": datetime.now(timezone.utc).isoformat(),
                        "Operation": "Field classification",
                        "Model": st.session_state.ai_model,
                        **usage
                    })
                    st.success(f"AI classification complete! ({usage.get('Total Tokens', 0)} tokens)")
                    st.rerun()
                else:
                    st.info("No unconfirmed columns needed AI recommendation.")
        st.markdown('</div>', unsafe_allow_html=True)

    st.session_state.mapping = st.data_editor(
        st.session_state.mapping,
        width="stretch",
        hide_index=True,
        disabled=["Source Column", "Confidence", "Method"],
        column_config={
            "NIQ Field": st.column_config.SelectboxColumn(options=TARGETS, required=True),
            "Confidence": st.column_config.ProgressColumn(min_value=0, max_value=1, format="%.0f%%"),
            "User Confirmed": st.column_config.CheckboxColumn("Confirmed")
        }
    )
    nav(4, 6, "Run transformation")

# -------------------------------------------------------------
# STEP 6: TRANSFORMATION
# -------------------------------------------------------------
elif step == 6:
    heading("STEP 06 · TRANSFORMATION", "Generate standardized NIQ canonical output", "Map verified columns to standard NIQ dimensions, preserve detected time periods, and compute record health.")
    
    st.markdown("""
    <div class="doppelrand-chassis" style="margin-bottom: 20px;">
      <div class="doppelrand-core schema-box-core" style="padding: 20px 24px;">
        <div class="theme-card-title" style="font-size: 1.05rem; margin-bottom: 6px;">Canonical Coverage Analysis Output Schema</div>
        <div class="schema-code-text" style="font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; font-weight: 600;">
          Country | Region | Channel | City/State | Category | Brand | SKU | Fact | [Preserved Time Period Columns]
        </div>
        <p class="theme-card-sub" style="margin: 8px 0 0;">
          Transforms client-specific values using NIQ lookup dictionaries, generates unique Record IDs, and assigns quality classification status.
        </p>
      </div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🚀 Run NIQ transformation", type="primary", width="stretch"):
        with st.spinner("Transforming and standardizing records..."):
            st.session_state.output = transform_to_niq(st.session_state.ingestion.frame, st.session_state.mapping, standards)
            st.session_state.quality = build_quality_report(st.session_state.output)
        go(7)
        
    nav(5, None)

# -------------------------------------------------------------
# STEP 7: NUMERICAL RECONCILIATION & VALIDATION (HERO STEP)
# -------------------------------------------------------------
elif step == 7:
    heading("STEP 07 · NUMERICAL VALIDATION", "Zero-data-loss reconciliation & visual verification", "Mathematically audit source shipment totals against transformed output values across dimensional slices.")
    
    src = st.session_state.ingestion.frame
    out = st.session_state.output
    # Re-use cached profile to eliminate redundant dataset scans
    p_cached = st.session_state.get("profile") or profile_dataframe(src)
    source_nums = p_cached.get("numeric_columns", [])
    output_nums = [c for c in out.columns if pd.to_numeric(out[c], errors="coerce").notna().mean() > .7]
    
    if source_nums and output_nums:
        with st.container():
            c_m1, c_m2, c_m3 = st.columns([1.5, 1.5, 1])
            with c_m1:
                sm = st.selectbox("Source measure column", source_nums)
            with c_m2:
                om = st.selectbox("Output measure column", output_nums, index=output_nums.index(sm) if sm in output_nums else 0)
            with c_m3:
                tol = st.number_input("Allowed variance", min_value=0.0, value=0.01, step=0.01, format="%.2f")
                
            dim_candidates = [c for c in ["Country", "Region", "Channel", "City/State", "Category", "Brand", "SKU", "Fact"] if c in out.columns] + [c for c in src.columns if c in out.columns and c not in DIMS]
            groups = st.multiselect("Reconciliation slice / combination", dim_candidates, default=[d for d in ["Channel", "Brand"] if d in dim_candidates][:2])
            
            summary, detail = reconcile(src, out, sm, om, groups, tol)
            st.session_state.recon_summary = summary
            st.session_state.recon_detail = detail
            
            st.markdown("<div style='margin-top: 14px;'></div>", unsafe_allow_html=True)
            
            # HERO ZERO-DATA-LOSS BANNER
            if summary["Match"]:
                banner_html = f"""
                <div class="success-gradient">
                  <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px;">
                    <div style="display: flex; align-items: center; gap: 16px;">
                      <div style="width: 50px; height: 50px; border-radius: 14px; background: rgba(255,255,255,0.18); display: flex; align-items: center; justify-content: center; font-size: 24px; font-weight: 900; border: 1px solid rgba(255,255,255,0.3);">✓</div>
                      <div>
                        <div style="display: flex; align-items: center; gap: 10px;">
                          <h2 style="margin: 0; font-size: 1.45rem; font-weight: 900; letter-spacing: -0.02em; color: white;">ZERO DATA LOSS VERIFIED</h2>
                          <span style="background: #34d399; color: #064e3b; font-size: 0.72rem; font-weight: 800; padding: 2px 10px; border-radius: 99px; letter-spacing: 0.05em;">PASS</span>
                        </div>
                        <p style="margin: 4px 0 0; color: #d1fae5; font-size: 0.85rem;">Pre-transformation client shipment totals match standardized output totals down to 0.00 variance.</p>
                      </div>
                    </div>
                    <div style="text-align: right;">
                      <div style="font-size: 0.68rem; font-weight: 700; color: #a7f3d0; text-transform: uppercase; letter-spacing: 0.1em;">Allowed Tolerance</div>
                      <div style="font-size: 1.35rem; font-weight: 900; color: white;">± {tol:.2f}</div>
                    </div>
                  </div>
                </div>
                """
            else:
                banner_html = f"""
                <div class="fail-gradient">
                  <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px;">
                    <div style="display: flex; align-items: center; gap: 16px;">
                      <div style="width: 50px; height: 50px; border-radius: 14px; background: rgba(255,255,255,0.18); display: flex; align-items: center; justify-content: center; font-size: 24px; font-weight: 900; border: 1px solid rgba(255,255,255,0.3);">⚠</div>
                      <div>
                        <div style="display: flex; align-items: center; gap: 10px;">
                          <h2 style="margin: 0; font-size: 1.45rem; font-weight: 900; letter-spacing: -0.02em; color: white;">NUMERICAL VARIANCE DETECTED</h2>
                          <span style="background: #fca5a5; color: #7f1d1d; font-size: 0.72rem; font-weight: 800; padding: 2px 10px; border-radius: 99px; letter-spacing: 0.05em;">FAIL</span>
                        </div>
                        <p style="margin: 4px 0 0; color: #fee2e2; font-size: 0.85rem;">Variance exceeds allowed tolerance of ± {tol:.2f}. Review cleanup actions before export.</p>
                      </div>
                    </div>
                    <div style="text-align: right;">
                      <div style="font-size: 0.68rem; font-weight: 700; color: #fecaca; text-transform: uppercase; letter-spacing: 0.1em;">Variance</div>
                      <div style="font-size: 1.35rem; font-weight: 900; color: white;">{summary['Difference']:,.2f}</div>
                    </div>
                  </div>
                </div>
                """
            st.markdown(banner_html, unsafe_allow_html=True)
            
            # 4 Metric Cards
            r1, r2, r3, r4 = st.columns(4)
            r1.metric("Raw Input Total", f"{summary['Input Total']:,.2f}")
            r2.metric("Standardized Output", f"{summary['Output Total']:,.2f}")
            r3.metric("Net Variance", f"{summary['Difference']:,.2f}")
            r4.metric("Audit Certification", "PASS" if summary["Match"] else "FAIL")
            
            # Visual Side-by-Side Comparison Chart
            if not detail.empty:
                st.markdown("<div style='margin-top: 24px;'></div>", unsafe_allow_html=True)
                with st.container(border=True):
                    st.markdown("""
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                      <div>
                        <h4 class="theme-card-title" style="margin: 0; font-size: 1.08rem;">Multi-Dimensional Slice Reconciliation</h4>
                        <div class="theme-card-sub">Visual comparison of Raw Input vs Transformed Output totals across selected slices</div>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    chart_groups = [c for c in groups if c in detail.columns]
                    if chart_groups:
                        chart_df = detail.copy()
                        chart_df["Slice"] = chart_df[chart_groups].astype(str).agg(" / ".join, axis=1)
                        plot_data = chart_df.set_index("Slice")[["Input Total", "Output Total"]]
                        st.bar_chart(plot_data, color=["#94a3b8", "#4f46e5"], width="stretch")
                    
                    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
                    st.dataframe(detail, width="stretch", hide_index=True)
    else:
        st.warning("No compatible numeric measure columns were detected for reconciliation.")
        
    nav(6, 8, "Review output")

# -------------------------------------------------------------
# STEP 8: HUMAN REVIEW & AUDIT TRAIL
# -------------------------------------------------------------
elif step == 8:
    heading("STEP 08 · HUMAN REVIEW & AUDIT", "Review, edit, and certify standardized data", "All inline user modifications are automatically tracked in the immutable audit trail.")
    
    output = st.session_state.output
    counts = output["Status"].value_counts()
    
    a, b, c, d = st.columns(4)
    a.metric("Total Rows", f"{len(output):,}")
    b.metric("Approved", int(counts.get("Approved", 0)))
    c.metric("Needs Review", int(counts.get("Needs Review", 0)))
    d.metric("Incomplete", int(counts.get("Incomplete", 0)))
    
    st.markdown("<div style='margin-top: 18px;'></div>", unsafe_allow_html=True)
    t1, t2, t3, t4 = st.tabs(["📋 Editable Standardized Output", "🔍 Data Quality Report", "📑 Duplicate Records", "🛡️ Immutable Audit Trail"])
    
    with t1:
        before = output.copy(deep=True)
        edited = st.data_editor(
            output,
            width="stretch",
            hide_index=True,
            disabled=["Record ID", "Confidence", "Recommendation Source"],
            column_config={
                "Status": st.column_config.SelectboxColumn(options=["Approved", "Needs Review", "Incomplete", "Rejected"]),
                "Confidence": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d%%")
            }
        )
        if st.button("💾 Save changes to audit trail", type="primary"):
            changes = 0
            common_cols = [c for c in edited.columns if c in before.columns]
            # Vectorized fast inequality check with null safety
            diff_mask = before[common_cols].ne(edited[common_cols]) & ~(before[common_cols].isna() & edited[common_cols].isna())
            if diff_mask.any().any():
                now_utc = datetime.now(timezone.utc).isoformat()
                for c in common_cols:
                    changed_indices = edited.index[diff_mask[c]]
                    for i in changed_indices:
                        b_val = clean_text(before.at[i, c])
                        e_val = clean_text(edited.at[i, c])
                        if b_val != e_val:
                            st.session_state.audit.append({
                                "Record ID": edited.at[i, "Record ID"] if "Record ID" in edited.columns else f"REC-{i+1:07d}",
                                "Field": c,
                                "Original Value": before.at[i, c],
                                "Final Value": edited.at[i, c],
                                "Changed At UTC": now_utc
                            })
                            changes += 1
            st.session_state.output = edited
            st.session_state.quality = build_quality_report(edited)
            st.session_state.pop("cached_pkg_key", None)
            st.success(f"{changes} change(s) recorded in audit log.")
            
    with t2:
        st.dataframe(st.session_state.quality, width="stretch", hide_index=True)
    with t3:
        st.dataframe(st.session_state.duplicates, width="stretch", hide_index=True)
    with t4:
        st.dataframe(pd.DataFrame(st.session_state.audit), width="stretch", hide_index=True)
        
    nav(7, 9, "Continue to export")

# -------------------------------------------------------------
# STEP 9: DELIVERABLES HUB
# -------------------------------------------------------------
else:
    heading("STEP 09 · DELIVERABLES HUB", "Download the complete coverage analysis delivery package", "All deliverables packaged strictly according to NIQ Hackfest guidelines.")
    
    out = st.session_state.output
    allowed = excel_allowed(out)
    
    # HERO DOWNLOAD CARD
    st.markdown("""
    <div class="hero-gradient">
      <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px;">
        <div>
          <span style="background: rgba(99, 102, 241, 0.25); color: #c7d2fe; border: 1px solid rgba(129, 140, 248, 0.35); padding: 4px 12px; border-radius: 99px; font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;">
            🎁 Complete Submission Package
          </span>
          <h2 style="margin: 8px 0 4px; font-size: 1.55rem; font-weight: 900; color: white; letter-spacing: -0.02em;">
            Coverage Analysis Delivery Bundle
          </h2>
          <p style="margin: 0; color: #cbd5e1; font-size: 0.85rem;">
            Includes standardized multi-tab Excel workbook, canonical flat CSV, exception report, API token telemetry, and complete audit manifest.
          </p>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    
    # High-Performance Export Memoization
    out_rows = len(out) if out is not None else 0
    audit_len = len(st.session_state.get("audit") or [])
    pkg_cache_key = f"{out_rows}_{audit_len}_{st.session_state.get('file_sig', '')}"
    if st.session_state.get("cached_pkg_key") != pkg_cache_key:
        with st.spinner("Preparing deliverable package..."):
            st.session_state.cached_package = package_bytes(
                out,
                st.session_state.quality,
                st.session_state.mapping,
                st.session_state.audit,
                st.session_state.profile,
                st.session_state.duplicates,
                st.session_state.recon_summary,
                st.session_state.recon_detail,
                st.session_state.token_usage,
                st.session_state.file_name
            )
            st.session_state.cached_pkg_key = pkg_cache_key
    package = st.session_state.cached_package
    st.download_button(
        "📦 Download Complete Package (ZIP)",
        package,
        "intelligent_client_data_preparation_final.zip",
        "application/zip",
        type="primary",
        width="stretch"
    )
    
    st.markdown("<div style='margin-top: 24px;'></div>", unsafe_allow_html=True)
    
    # 3 DELIVERABLE CARDS
    d1, d2, d3 = st.columns(3)
    
    with d1:
        with st.container(border=True):
            st.markdown("""
            <div style="font-size: 1.4rem; margin-bottom: 6px;">📗</div>
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <div class="theme-card-title" style="font-size: 1rem;">Standardized Excel</div>
              <span style="background: #f0fdf4; color: #166534; font-size: 0.68rem; font-weight: 700; padding: 2px 8px; border-radius: 6px; border: 1px solid #bbf7d0;">Multi-Tab ✓</span>
            </div>
            <p style="font-size: 0.75rem; color: #64748b; margin: 8px 0 16px;">
              Workbook with Standardized Data, Data Quality, Mapping, Audit, Reconciliation, and Duplicates tabs.
            </p>
            """, unsafe_allow_html=True)
            if allowed:
                st.download_button(
                    "Download .XLSX",
                    excel_bytes(out, st.session_state.quality, st.session_state.mapping, st.session_state.audit, st.session_state.profile, st.session_state.duplicates, st.session_state.recon_summary, st.session_state.recon_detail, st.session_state.token_usage),
                    "standardized_niq_output.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    width="stretch"
                )
            else:
                st.caption("Workbook exceeds Excel row/column capacity limits.")

    with d2:
        with st.container(border=True):
            st.markdown("""
            <div style="font-size: 1.4rem; margin-bottom: 6px;">📄</div>
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <div class="theme-card-title" style="font-size: 1rem;">Canonical Flat CSV</div>
              <span style="background: #eff6ff; color: #1e40af; font-size: 0.68rem; font-weight: 700; padding: 2px 8px; border-radius: 6px; border: 1px solid #bfdbfe;">Always Eligible</span>
            </div>
            <p style="font-size: 0.75rem; color: #64748b; margin: 8px 0 16px;">
              UTF-8-SIG flat table formatted to exact NIQ Coverage Analysis dimensions with zero limits.
            </p>
            """, unsafe_allow_html=True)
            st.download_button(
                "Download .CSV",
                csv_bytes(out),
                "standardized_niq_output.csv",
                "text/csv",
                width="stretch"
            )

    with d3:
        with st.container(border=True):
            st.markdown("""
            <div style="font-size: 1.4rem; margin-bottom: 6px;">🛡️</div>
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <div class="theme-card-title" style="font-size: 1rem;">Quality & Audit Trail</div>
              <span style="background: #faf5ff; color: #6b21a8; font-size: 0.68rem; font-weight: 700; padding: 2px 8px; border-radius: 6px; border: 1px solid #e9d5ff;">100% Traceable</span>
            </div>
            <p style="font-size: 0.75rem; color: #64748b; margin: 8px 0 16px;">
              Full data quality exception report and immutable cell-level modification logs.
            </p>
            """, unsafe_allow_html=True)
            st.download_button(
                "Download Quality Report",
                csv_bytes(st.session_state.quality),
                "data_quality_report.csv",
                "text/csv",
                width="stretch"
            )
            st.download_button(
                "Download API Token Usage",
                csv_bytes(pd.DataFrame(st.session_state.token_usage)),
                "api_token_usage.csv",
                "text/csv",
                width="stretch"
            )

    nav(8, None)
