import React from "react";
import { ChartInfo } from "@/lib/types";

export function ChartDisplay({ chart }: { chart: ChartInfo }) {
  if (!chart.b64) return null;
  const src = `data:image/png;base64,${chart.b64}`;

  return (
    <div className="my-4 rounded-lg border bg-card text-card-foreground shadow-sm max-w-4xl">
      <div className="flex flex-col space-y-1.5 p-4 border-b">
        <h3 className="text-lg font-semibold leading-none tracking-tight">
          {chart.title || "Generated Chart"}
        </h3>
        <p className="text-sm text-muted-foreground capitalize">
          {chart.type} Chart
        </p>
      </div>
      <div className="p-4 flex items-center justify-center bg-white rounded-b-lg">
        <img
          src={src}
          alt={chart.title || "Analysis Chart"}
          className="max-w-full h-auto object-contain rounded-md max-h-[500px]"
        />
      </div>
    </div>
  );
}
