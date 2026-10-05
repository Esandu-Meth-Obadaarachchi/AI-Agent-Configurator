"use client";

import {
  ArrowsClockwise,
  Books,
  Brain,
  Calculator,
  ChatCircleText,
  Code,
  Database,
  FileHtml,
  GitFork,
  Globe,
  HandPalm,
  type Icon,
  MagnifyingGlass,
  PaperPlaneTilt,
  Plug,
  PlugsConnected,
  Robot,
  ShieldCheck,
  Sparkle,
  UsersThree,
  Wrench,
} from "@phosphor-icons/react";

const ICONS: Record<string, Icon> = {
  ArrowsClockwise,
  Books,
  Brain,
  Calculator,
  ChatCircleText,
  Code,
  Database,
  FileHtml,
  GitFork,
  Globe,
  HandPalm,
  MagnifyingGlass,
  PaperPlaneTilt,
  Plug,
  PlugsConnected,
  Robot,
  ShieldCheck,
  Sparkle,
  UsersThree,
  Wrench,
};

export function BlockIcon({ name, size = 16, className }: { name: string; size?: number; className?: string }) {
  const IconComponent = ICONS[name] ?? Wrench;
  return <IconComponent size={size} weight="duotone" className={className} aria-hidden />;
}
