import { Badge } from "@/components/ui/Badge";
import { ApprovalStepResponse } from "@/types/approval";

const STEP_TONE: Record<string, "success" | "danger" | "neutral"> = {
  approved: "success",
  rejected: "danger",
  pending: "neutral",
};

export function ApprovalTimeline({ steps }: { steps: ApprovalStepResponse[] }) {
  return (
    <ol className="space-y-3">
      {steps.map((step) => (
        <li key={step.step_number} className="flex items-center justify-between text-sm">
          <div>
            <span className="font-medium">Step {step.step_number}</span>
            <span className="ml-2 text-slate-500 capitalize">{step.required_role.replace("_", " ")}</span>
            {step.comment && <p className="mt-1 text-xs text-slate-500">&ldquo;{step.comment}&rdquo;</p>}
          </div>
          <Badge tone={STEP_TONE[step.status]}>{step.status}</Badge>
        </li>
      ))}
    </ol>
  );
}
