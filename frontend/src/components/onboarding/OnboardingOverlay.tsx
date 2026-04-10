import { useCallback, useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAppStore } from "../../lib/app-store";
import { useLang } from "../../lib/language";

type OnboardingStep = {
  route: "home" | "workspace";
  selector: string;
  zh: string;
  en: string;
  ensurePanels?: {
    leftOpen?: boolean;
    rightOpen?: boolean;
    topOpen?: boolean;
  };
};

const STEPS: OnboardingStep[] = [
  {
    route: "home",
    selector: "[data-guide='home-start']",
    zh: "从首页主按钮进入任务分流，先选模式再创建任务。",
    en: "Start from home CTA, choose mode first, then create a task."
  },
  {
    route: "workspace",
    ensurePanels: { leftOpen: true, topOpen: true },
    selector: "[data-guide='workspace-left']",
    zh: "左侧是任务对象树：任务、模块、运行批次和产物在这里追踪。",
    en: "Left panel is task object tree: task, module, run batches, and artifacts."
  },
  {
    route: "workspace",
    ensurePanels: { topOpen: true },
    selector: "[data-guide='workspace-center']",
    zh: "中间主舞台按阶段推进：输入校验、运行、证据绑定、一致性检查与导出。",
    en: "Center stage follows workflow steps: validate, run, bind evidence, check consistency, export."
  },
  {
    route: "workspace",
    ensurePanels: { rightOpen: true, topOpen: true },
    selector: "[data-guide='workspace-right']",
    zh: "右侧是持续在线状态流，显示阻塞原因和下一动作。",
    en: "Right panel is persistent status stream with blockers and next actions."
  }
] as const;

type OnboardingOverlayProps = {
  active: boolean;
  onClose: () => void;
};

export function OnboardingOverlay({ active, onClose }: OnboardingOverlayProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const { lang, t } = useLang();
  const { state, dispatch } = useAppStore();
  const [index, setIndex] = useState(0);
  const [rect, setRect] = useState<DOMRect | null>(null);

  const step = useMemo(() => STEPS[index], [index]);
  const text = lang === "zh" ? step.zh : step.en;
  const workspaceTaskId = state.taskSpaces[0]?.id;
  const targetPath = step.route === "home" ? "/" : workspaceTaskId ? `/workspace/${workspaceTaskId}` : "/tasks";

  const updateRect = useCallback(() => {
    const element = document.querySelector(step.selector);
    if (!element) {
      setRect(null);
      return;
    }
    setRect(element.getBoundingClientRect());
  }, [step.selector]);

  useEffect(() => {
    if (!active) return;
    if (location.pathname !== targetPath) {
      navigate(targetPath);
      return;
    }

    if (step.ensurePanels) {
      dispatch({ type: "set_panel_state", payload: step.ensurePanels });
    }

    let stopped = false;
    let viewportBound = false;
    let retryTimer: number | null = null;
    let raf1: number | null = null;
    let raf2: number | null = null;
    let settleTimer: number | null = null;

    const onViewportChange = () => updateRect();

    const bindViewportEvents = () => {
      if (viewportBound) return;
      viewportBound = true;
      window.addEventListener("resize", onViewportChange);
      window.addEventListener("scroll", onViewportChange, true);
    };

    const tryLocate = (attempt = 0) => {
      if (stopped) return;
      const element = document.querySelector(step.selector);
      if (!element) {
        if (attempt < 24) {
          retryTimer = window.setTimeout(() => tryLocate(attempt + 1), 80);
        } else {
          setRect(null);
        }
        return;
      }

      element.scrollIntoView({ block: "center", behavior: "smooth" });
      updateRect();
      bindViewportEvents();

      // Re-sample after smooth scroll / reveal animation settles.
      raf1 = window.requestAnimationFrame(updateRect);
      raf2 = window.requestAnimationFrame(() => window.requestAnimationFrame(updateRect));
      settleTimer = window.setTimeout(updateRect, 380);
    };

    tryLocate();

    return () => {
      stopped = true;
      if (retryTimer !== null) window.clearTimeout(retryTimer);
      if (raf1 !== null) window.cancelAnimationFrame(raf1);
      if (raf2 !== null) window.cancelAnimationFrame(raf2);
      if (settleTimer !== null) window.clearTimeout(settleTimer);
      if (viewportBound) {
        window.removeEventListener("resize", onViewportChange);
        window.removeEventListener("scroll", onViewportChange, true);
      }
    };
  }, [active, dispatch, location.pathname, navigate, step.ensurePanels, step.selector, targetPath, updateRect]);

  useEffect(() => {
    if (!active) {
      setIndex(0);
      setRect(null);
    }
  }, [active]);

  if (!active) {
    return null;
  }

  const next = () => {
    if (index >= STEPS.length - 1) {
      onClose();
      return;
    }
    setIndex((v) => v + 1);
  };

  const prev = () => {
    setIndex((v) => (v > 0 ? v - 1 : 0));
  };

  return (
    <div className="onboarding-wrap">
      {rect ? (
        <div
          className="onboarding-highlight"
          style={{
            top: `${rect.top - 8}px`,
            left: `${rect.left - 8}px`,
            width: `${rect.width + 16}px`,
            height: `${rect.height + 16}px`
          }}
        />
      ) : null}

      <div className="onboarding-card" data-guide="onboarding-card">
        <div className="text-xs tracking-[0.24em] text-scientific-700/75">{t("onboardingTitle")}</div>
        <p className="mt-2 text-sm text-scientific-900">{text}</p>
        <div className="mt-2 text-xs text-scientific-700/80">{index + 1} / {STEPS.length}</div>

        <div className="mt-4 flex justify-between gap-2">
          <div className="flex gap-2">
            <button className="pill-btn" onClick={prev} disabled={index === 0}>{t("onboardingPrev")}</button>
            <button className="pill-btn" onClick={onClose}>{t("onboardingSkip")}</button>
          </div>
          <button className="pill-btn-primary" onClick={next}>{index >= STEPS.length - 1 ? t("onboardingDone") : t("onboardingNext")}</button>
        </div>
      </div>
    </div>
  );
}
