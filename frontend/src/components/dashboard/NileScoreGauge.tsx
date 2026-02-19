"use client";

import { cn, gradeColor, scoreToGrade } from "@/lib/utils";

interface NileScoreGaugeProps {
  score: number;
  size?: "sm" | "md" | "lg";
  label?: string;
}

export function NileScoreGauge({ score, size = "md", label }: NileScoreGaugeProps) {
  const grade = scoreToGrade(score);
  const circumference = 2 * Math.PI * 45;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  const sizeMap = { sm: "w-24 h-24", md: "w-36 h-36", lg: "w-48 h-48" };
  const textSizeMap = { sm: "text-lg", md: "text-2xl", lg: "text-4xl" };

  const strokeColor =
    score >= 80 ? "#22c55e" : score >= 60 ? "#f59e0b" : score >= 40 ? "#f97316" : "#ef4444";

  return (
    <div className="flex flex-col items-center gap-2">
      <div className={cn("relative", sizeMap[size])}>
        <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r="45" fill="none" stroke="#262626" strokeWidth="8" />
          <circle
            cx="50"
            cy="50"
            r="45"
            fill="none"
            stroke={strokeColor}
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            className="transition-all duration-1000 ease-out"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={cn("font-bold", textSizeMap[size], gradeColor(grade))}>{grade}</span>
          <span className="text-xs text-gray-400">{score.toFixed(1)}</span>
        </div>
      </div>
      {label && <span className="text-sm text-gray-400">{label}</span>}
    </div>
  );
}
