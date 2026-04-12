import React from "react";
import { motion } from "framer-motion";
import { ArrowRight, ShieldCheck, Globe, FileText, Scale, CheckCircle2, Search, Sparkles, AlertTriangle } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.6 } },
};

const sectionClass = "max-w-6xl mx-auto px-6 md:px-10";

const painPoints = [
  {
    title: "规则分散，判断容易出错",
    desc: "中国、欧盟、美国的跨境数据规则口径不同，企业很难快速判断适用路径与义务边界。",
    icon: Scale,
  },
  {
    title: "材料复杂，文书成本高",
    desc: "从数据清单、实体清单到影响评估、风险自评估，准备过程长、协同成本高、反复修改频繁。",
    icon: FileText,
  },
  {
    title: "审查标准不稳定，缺口难定位",
    desc: "很多问题并不是完全没有做，而是做得不完整、不一致、不足以支撑监管或客户审查。",
    icon: AlertTriangle,
  },
];

const modules = [
  {
    title: "合规路径诊断",
    desc: "基于问答、规则树与事实抽取，判断应走哪条路径、为什么、下一步做什么。",
    tag: "Diagnosis",
  },
  {
    title: "报告草案生成",
    desc: "自动生成风险自评估、PIPIA、DPIA、TIA 等文书草案，保留人工复核接口。",
    tag: "Drafting",
  },
  {
    title: "合同与文件审查",
    desc: "针对隐私政策、数据处理协议、标准合同、SCC/BCR 等文件做条款级检查与修改建议。",
    tag: "Review",
  },
  {
    title: "风险整改清单",
    desc: "把发现的问题转化为可执行任务，按优先级、责任域和整改动作输出。",
    tag: "Action",
  },
];

const jurisdictions = [
  {
    name: "中国",
    points: ["安全评估路径", "标准合同路径", "个人信息出境认证", "PIPIA 与材料审查"],
  },
  {
    name: "欧盟",
    points: ["SCC / BCR 审查", "DPIA 草案生成", "TIA 草案生成", "跨境传输义务分析"],
  },
  {
    name: "美国",
    points: ["14117 行政令风险识别", "CPRA 合规全景审查", "UI 暗模式识别", "第三方共享风险分析"],
  },
];

const flow = [
  "输入企业与业务事实",
  "系统抽取关键字段并做规则匹配",
  "形成报告、矩阵与风险结论",
  "输出整改建议与后续动作",
];

export default function Ai4LawHomepageDraft() {
  return (
    <div className="min-h-screen bg-[#f8f6f1] text-slate-900">
      <div className="fixed inset-x-0 top-0 z-50 border-b border-black/5 bg-[#f8f6f1]/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4 md:px-10">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-slate-900 text-white">
              <Scale className="h-5 w-5" />
            </div>
            <div>
              <div className="text-sm font-semibold tracking-[0.18em] text-slate-500">AI4LAW</div>
              <div className="text-sm text-slate-700">跨境数据合规智能助手</div>
            </div>
          </div>
          <div className="hidden items-center gap-8 text-sm text-slate-700 md:flex">
            <a href="#overview" className="hover:text-slate-950">产品概览</a>
            <a href="#modules" className="hover:text-slate-950">功能模块</a>
            <a href="#jurisdictions" className="hover:text-slate-950">法域支持</a>
            <a href="#flow" className="hover:text-slate-950">工作流程</a>
          </div>
        </div>
      </div>

      <section className="relative overflow-hidden pt-28 md:pt-36">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(190,210,255,0.32),transparent_30%),radial-gradient(circle_at_top_right,rgba(255,220,200,0.32),transparent_26%),linear-gradient(to_bottom,#f8f6f1,#f8f6f1)]" />
        <div className={`${sectionClass} relative grid min-h-[88vh] items-center gap-14 py-12 md:grid-cols-[1.15fr_0.85fr] md:py-20`}>
          <motion.div initial="hidden" animate="visible" variants={fadeUp} className="space-y-8">
            <div className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white/70 px-4 py-2 text-sm text-slate-700 shadow-sm">
              <Sparkles className="h-4 w-4" />
              面向中国 / 欧盟 / 美国的数据跨境合规工作流
            </div>

            <div className="space-y-5">
              <h1 className="max-w-4xl text-4xl font-semibold leading-tight tracking-tight md:text-6xl md:leading-[1.08]">
                把复杂的跨境数据合规，
                <br className="hidden md:block" />
                变成清晰、可执行的工作流
              </h1>
              <p className="max-w-2xl text-base leading-8 text-slate-600 md:text-lg">
                从合规路径判断、材料收集、报告草案生成，到文件审查、风险定位与整改清单输出，
                为企业提供一套可落地的合规辅助前端入口。
              </p>
            </div>

            <div className="flex flex-wrap gap-4">
              <Button size="lg" className="rounded-2xl px-6">
                立即开始诊断
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
              <Button size="lg" variant="outline" className="rounded-2xl px-6 bg-white/70">
                查看功能模块
              </Button>
            </div>

            <div className="grid max-w-2xl grid-cols-1 gap-4 pt-4 sm:grid-cols-3">
              {[
                ["3 大法域", "中国 / 欧盟 / 美国"],
                ["4 类核心能力", "诊断 / 起草 / 审查 / 整改"],
                ["文书与规则双驱动", "不是只做问答或检索"],
              ].map(([title, desc]) => (
                <div key={title} className="rounded-2xl border border-slate-200 bg-white/75 p-4 shadow-sm">
                  <div className="text-sm font-semibold text-slate-900">{title}</div>
                  <div className="mt-1 text-sm leading-6 text-slate-600">{desc}</div>
                </div>
              ))}
            </div>
          </motion.div>

          <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7, delay: 0.1 }}>
            <div className="relative rounded-[32px] border border-white/60 bg-white/80 p-5 shadow-[0_24px_80px_rgba(15,23,42,0.10)] backdrop-blur">
              <div className="rounded-[28px] bg-slate-950 p-6 text-white">
                <div className="flex items-center justify-between border-b border-white/10 pb-4">
                  <div>
                    <div className="text-xs uppercase tracking-[0.2em] text-slate-400">Live Preview</div>
                    <div className="mt-1 text-xl font-semibold">合规路径智能诊断</div>
                  </div>
                  <ShieldCheck className="h-7 w-7 text-emerald-300" />
                </div>
                <div className="space-y-4 pt-5 text-sm">
                  {[
                    "企业是否属于受规制主体？",
                    "涉及哪些数据类型与跨境场景？",
                    "应走哪条合规路径？",
                    "需要生成哪些报告与补充材料？",
                  ].map((q, i) => (
                    <div key={q} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                      <div className="mb-2 text-xs text-slate-400">问题 {i + 1}</div>
                      <div className="text-base text-slate-100">{q}</div>
                    </div>
                  ))}
                </div>
              </div>
              <div className="absolute -bottom-5 -left-5 rounded-2xl border border-slate-200 bg-white px-4 py-3 shadow-lg">
                <div className="text-xs uppercase tracking-[0.18em] text-slate-500">Output</div>
                <div className="mt-1 text-sm font-medium">报告草案 + 风险矩阵 + 行动清单</div>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      <section id="overview" className="py-24 md:py-28">
        <div className={sectionClass}>
          <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={fadeUp} className="mx-auto max-w-3xl text-center">
            <div className="text-sm font-semibold tracking-[0.18em] text-slate-500">WHY THIS PRODUCT</div>
            <h2 className="mt-4 text-3xl font-semibold md:text-5xl">不是缺少信息，而是缺少一条清楚的合规主线</h2>
            <p className="mt-5 text-base leading-8 text-slate-600 md:text-lg">
              官网首页不只展示功能，更应该沿着用户的真实思考顺序展开：先看到问题，再理解方法，最后知道如何开始。
            </p>
          </motion.div>
          <div className="mt-14 grid gap-6 md:grid-cols-3">
            {painPoints.map((item, idx) => {
              const Icon = item.icon;
              return (
                <motion.div key={item.title} initial="hidden" whileInView="visible" viewport={{ once: true }} variants={{ ...fadeUp, visible: { ...fadeUp.visible, transition: { duration: 0.55, delay: idx * 0.08 } } }}>
                  <Card className="h-full rounded-[28px] border-slate-200 bg-white/80 shadow-sm">
                    <CardContent className="p-7">
                      <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-100">
                        <Icon className="h-6 w-6 text-slate-900" />
                      </div>
                      <h3 className="text-xl font-semibold">{item.title}</h3>
                      <p className="mt-3 text-sm leading-7 text-slate-600">{item.desc}</p>
                    </CardContent>
                  </Card>
                </motion.div>
              );
            })}
          </div>
        </div>
      </section>

      <section id="modules" className="bg-white py-24 md:py-28">
        <div className={sectionClass}>
          <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={fadeUp} className="grid gap-8 md:grid-cols-[0.9fr_1.1fr] md:items-end">
            <div>
              <div className="text-sm font-semibold tracking-[0.18em] text-slate-500">HOW IT WORKS</div>
              <h2 className="mt-4 text-3xl font-semibold md:text-5xl">一个层层下滑、逻辑递进的首页草稿</h2>
            </div>
            <p className="max-w-2xl text-base leading-8 text-slate-600 md:justify-self-end md:text-lg">
              参考你给的网站，它的强项不在“内容多”，而在“叙事连续”。这里先做一个适合 AI4Law 的草稿：首页从产品定位开始，顺着问题、方案、法域、流程，逐屏推进。
            </p>
          </motion.div>

          <div className="mt-14 grid gap-6 md:grid-cols-2">
            {modules.map((m, idx) => (
              <motion.div key={m.title} initial="hidden" whileInView="visible" viewport={{ once: true }} variants={{ ...fadeUp, visible: { ...fadeUp.visible, transition: { duration: 0.55, delay: idx * 0.07 } } }}>
                <Card className="h-full rounded-[28px] border-slate-200 bg-[#f8f6f1] shadow-sm">
                  <CardContent className="p-7 md:p-8">
                    <div className="mb-4 inline-flex rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-medium uppercase tracking-[0.16em] text-slate-500">
                      {m.tag}
                    </div>
                    <h3 className="text-2xl font-semibold">{m.title}</h3>
                    <p className="mt-3 text-sm leading-7 text-slate-600 md:text-base">{m.desc}</p>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      <section id="jurisdictions" className="py-24 md:py-28">
        <div className={sectionClass}>
          <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={fadeUp} className="flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
            <div>
              <div className="text-sm font-semibold tracking-[0.18em] text-slate-500">JURISDICTIONS</div>
              <h2 className="mt-4 text-3xl font-semibold md:text-5xl">不同法域，不同规则，同一套交互入口</h2>
            </div>
            <div className="max-w-2xl text-base leading-8 text-slate-600 md:text-lg">
              面向官网展示时，这一屏负责回答：这个系统不是抽象的“法律 AI”，而是明确覆盖中国、欧盟、美国三类核心跨境数据场景。
            </div>
          </motion.div>

          <div className="mt-14 grid gap-6 md:grid-cols-3">
            {jurisdictions.map((j, idx) => (
              <motion.div key={j.name} initial="hidden" whileInView="visible" viewport={{ once: true }} variants={{ ...fadeUp, visible: { ...fadeUp.visible, transition: { duration: 0.55, delay: idx * 0.08 } } }}>
                <Card className="h-full rounded-[28px] border-slate-200 bg-white/80 shadow-sm">
                  <CardContent className="p-7">
                    <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-100">
                      <Globe className="h-6 w-6 text-slate-900" />
                    </div>
                    <h3 className="text-2xl font-semibold">{j.name}</h3>
                    <div className="mt-5 space-y-3">
                      {j.points.map((p) => (
                        <div key={p} className="flex items-start gap-3 text-sm leading-6 text-slate-700">
                          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                          <span>{p}</span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      <section id="flow" className="bg-slate-950 py-24 text-white md:py-28">
        <div className={sectionClass}>
          <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={fadeUp} className="grid gap-10 md:grid-cols-[0.85fr_1.15fr]">
            <div>
              <div className="text-sm font-semibold tracking-[0.18em] text-slate-400">WORKFLOW</div>
              <h2 className="mt-4 text-3xl font-semibold md:text-5xl">最后一屏，要把复杂工作流讲成四步</h2>
              <p className="mt-5 text-base leading-8 text-slate-300 md:text-lg">
                这部分适合做成滚动叙事、时间轴或分步卡片，让用户在最短路径内理解你们的产品闭环。
              </p>
            </div>

            <div className="grid gap-4">
              {flow.map((step, idx) => (
                <motion.div key={step} initial="hidden" whileInView="visible" viewport={{ once: true }} variants={{ ...fadeUp, visible: { ...fadeUp.visible, transition: { duration: 0.5, delay: idx * 0.08 } } }} className="flex items-center gap-5 rounded-[28px] border border-white/10 bg-white/5 p-5 md:p-6">
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-white text-slate-900">
                    <span className="text-lg font-semibold">0{idx + 1}</span>
                  </div>
                  <div className="text-lg font-medium text-slate-100">{step}</div>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </div>
      </section>

      <section className="py-24 md:py-28">
        <div className={sectionClass}>
          <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={fadeUp} className="rounded-[36px] border border-slate-200 bg-white px-8 py-12 text-center shadow-sm md:px-16 md:py-16">
            <div className="mx-auto max-w-3xl">
              <div className="text-sm font-semibold tracking-[0.18em] text-slate-500">NEXT STEP</div>
              <h2 className="mt-4 text-3xl font-semibold md:text-5xl">这是首页草稿，不是最终视觉稿</h2>
              <p className="mt-5 text-base leading-8 text-slate-600 md:text-lg">
                当前先把信息结构、滚动叙事和视觉气质搭起来。下一步可以再细化成你项目自己的正式版本，包括文案替换、插画、配色、动画节奏和具体模块跳转。
              </p>
            </div>
            <div className="mt-8 flex flex-wrap justify-center gap-4">
              <Button size="lg" className="rounded-2xl px-6">
                继续细化文案
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
              <Button size="lg" variant="outline" className="rounded-2xl px-6">
                调整成法律科技风格
              </Button>
            </div>
          </motion.div>
        </div>
      </section>
    </div>
  );
}
