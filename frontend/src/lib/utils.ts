import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function gradeColor(grade: string): string {
  switch (grade) {
    case "A+":
    case "A":
      return "text-security-safe";
    case "B":
      return "text-yellow-400";
    case "C":
      return "text-security-warning";
    case "D":
      return "text-orange-500";
    default:
      return "text-security-danger";
  }
}

export function scoreToGrade(score: number): string {
  if (score >= 90) return "A+";
  if (score >= 80) return "A";
  if (score >= 70) return "B";
  if (score >= 60) return "C";
  if (score >= 50) return "D";
  return "F";
}

export function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}
