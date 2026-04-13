import { LandingPage } from "../components/landing/LandingPage";
import type { Jurisdiction, LaunchMode } from "../lib/domain";

type HomePageProps = {
  onStart: () => void;
  onQuickCreate: (config: {
    mode: LaunchMode;
    name: string;
    jurisdiction: Jurisdiction;
    taskTemplateId: string;
  }) => void;
};

export function HomePage({ onStart, onQuickCreate }: HomePageProps) {
  return <LandingPage onStart={onStart} onQuickCreate={onQuickCreate} />;
}
