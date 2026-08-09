/**
 * 首页组件
 *
 * 该组件用于展示应用程序的首页内容，包括应用品牌、标题、简介和操作按钮。
 * 用户可以通过点击“开始”按钮进入应用程序的主要功能，或者通过快速创建任务空间的方式快速开始工作。
 *
 * @param {Object} props - 组件的属性对象
 * @param {Function} props.onStart - 点击“开始”按钮时的回调函数
 * @param {Function} props.onQuickCreate - 快速创建任务空间时的回调函数，接收一个配置对象作为参数
 */
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
