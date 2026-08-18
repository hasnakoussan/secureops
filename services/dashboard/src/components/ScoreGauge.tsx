import type { Classification } from "../lib/scans";

const RISK_COLORS: Record<Classification, string> = {
  Safe: "var(--color-risk-safe)",
  Warning: "var(--color-risk-warning)",
  Critical: "var(--color-risk-critical)",
};

interface ScoreGaugeProps {
  score: number;
  classification: Classification;
  size?: number;
}

export function ScoreGauge({ score, classification, size = 96 }: ScoreGaugeProps) {
  const strokeWidth = size * 0.08;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - score / 100);
  const color = RISK_COLORS[classification];

  return (
    <div
      className="relative inline-flex items-center justify-center"
      style={{ width: size, height: size }}
      role="img"
      aria-label={`Score de risque : ${score} sur 100, classification ${classification}`}
    >
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--color-border)"
          strokeWidth={strokeWidth}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-[stroke-dashoffset] duration-700 ease-out"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span
          className="font-mono font-semibold leading-none"
          style={{ fontSize: size * 0.28, color }}
        >
          {score}
        </span>
        {size >= 80 && (
          <span
            className="font-mono uppercase tracking-wide text-[var(--color-text-muted)] mt-1"
            style={{ fontSize: size * 0.1 }}
          >
            {classification}
          </span>
        )}
      </div>
    </div>
  );
}
