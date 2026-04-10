import { LandingPage } from "../components/landing/LandingPage";

type HomePageProps = {
  onStart: () => void;
};

export function HomePage({ onStart }: HomePageProps) {
  return <LandingPage onStart={onStart} />;
}
