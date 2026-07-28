import { Card } from "@/components/ui/Card";

export function ComingSoon({ title, description }: { title: string; description: string }) {
  return (
    <div>
      <h1 className="mb-6 text-2xl font-semibold">{title}</h1>
      <Card>
        <p className="text-sm text-slate-600">{description}</p>
      </Card>
    </div>
  );
}
