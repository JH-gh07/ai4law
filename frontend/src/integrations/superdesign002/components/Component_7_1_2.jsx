import Component_7_1_2_1 from './Component_7_1_2_1';
import Component_7_1_2_2 from './Component_7_1_2_2';
import Component_7_1_2_3 from './Component_7_1_2_3';
import Component_7_1_2_4 from './Component_7_1_2_4';
import Component_7_1_2_5 from './Component_7_1_2_5';
import Component_7_1_2_6 from './Component_7_1_2_6';

function Component_7_1_2() {
  return (
    <div
      aria-hidden="true"
      className="min-h-0 absolute z-0 hidden caret-zinc-950 [color-scheme:light] inset-0"
      data-component-id="Component_7_1_2"
    >
      <div className="h-full overflow-x-hidden caret-zinc-950 [color-scheme:light]">
        <div className="min-h-full max-w-[1120px] flex flex-col caret-zinc-950 [color-scheme:light] mx-auto pt-5 pb-10 px-8">
          <Component_7_1_2_1 />
          <Component_7_1_2_2 />
          <Component_7_1_2_3 />
          <Component_7_1_2_4 />
          <section className="[content-visibility:auto] [contain-intrinsic-width:720px] [contain-intrinsic-height:720px] [border-right-style:dashed] [border-bottom-style:dashed] [border-left-style:dashed] caret-zinc-950 [color-scheme:light] [border-top-style:dashed] py-6 border-[rgba(0,0,0,0.12)] border-t">
            <div className="flex flex-wrap justify-between items-start gap-y-3 gap-x-3 caret-zinc-950 [color-scheme:light] mb-5">
              <div className="min-w-0 caret-zinc-950 [color-scheme:light]">
                <div className="text-zinc-500 font-semibold text-[11px] tracking-[1.98px] uppercase caret-zinc-500 [color-scheme:light]">
                  Next Step
                </div>
                <div className="text-zinc-500 leading-[28px] text-[14px] max-w-screen-md caret-zinc-500 [color-scheme:light] mt-2">
                  This section turns the latest durable guidance into a compact
                  execution brief.
                </div>
              </div>
            </div>
            <div className="text-zinc-500 leading-[28px] text-[14px] caret-zinc-500 [color-scheme:light] py-3">
              Durable guidance will appear after the next stage-significant
              update.
            </div>
          </section>
          <section className="[content-visibility:auto] [contain-intrinsic-width:720px] [contain-intrinsic-height:720px] [border-right-style:dashed] [border-bottom-style:dashed] [border-left-style:dashed] caret-zinc-950 [color-scheme:light] [border-top-style:dashed] py-6 border-[rgba(0,0,0,0.12)] border-t">
            <div className="flex flex-wrap justify-between items-start gap-y-3 gap-x-3 caret-zinc-950 [color-scheme:light] mb-5">
              <div className="min-w-0 caret-zinc-950 [color-scheme:light]">
                <div className="text-zinc-500 font-semibold text-[11px] tracking-[1.98px] uppercase caret-zinc-500 [color-scheme:light]">
                  Idea Lines
                </div>
                <div className="text-zinc-500 leading-[28px] text-[14px] max-w-screen-md caret-zinc-500 [color-scheme:light] mt-2">
                  This is the minimal audit view for each idea line: whether it
                  has reached a main run, whether it owns a paper line, and
                  whether supplementary work is still open.
                </div>
              </div>
            </div>
            <div className="min-w-0 caret-zinc-950 [color-scheme:light]">
              <div className="text-zinc-500 leading-[28px] text-[14px] caret-zinc-500 [color-scheme:light] py-3">
                No durable idea lines are exposed yet.
              </div>
            </div>
          </section>
          <Component_7_1_2_5 />
          <section className="[content-visibility:auto] [contain-intrinsic-width:720px] [contain-intrinsic-height:720px] [border-right-style:dashed] [border-bottom-style:dashed] [border-left-style:dashed] caret-zinc-950 [color-scheme:light] [border-top-style:dashed] py-6 border-[rgba(0,0,0,0.12)] border-t">
            <div className="flex flex-wrap justify-between items-start gap-y-3 gap-x-3 caret-zinc-950 [color-scheme:light] mb-5">
              <div className="min-w-0 caret-zinc-950 [color-scheme:light]">
                <div className="text-zinc-500 font-semibold text-[11px] tracking-[1.98px] uppercase caret-zinc-500 [color-scheme:light]">
                  Paper Contract Health
                </div>
                <div className="text-zinc-500 leading-[28px] text-[14px] max-w-screen-md caret-zinc-500 [color-scheme:light] mt-2">
                  This is the minimal blocking surface for the active paper
                  line. If this section is not green, the system should repair
                  the paper contract or complete required supplementary work
                  before treating the paper as settled.
                </div>
              </div>
            </div>
            <div className="text-zinc-500 leading-[28px] text-[14px] caret-zinc-500 [color-scheme:light] py-3">
              No paper-contract health summary is exposed yet.
            </div>
          </section>
          <section className="[content-visibility:auto] [contain-intrinsic-width:720px] [contain-intrinsic-height:720px] [border-right-style:dashed] [border-bottom-style:dashed] [border-left-style:dashed] caret-zinc-950 [color-scheme:light] [border-top-style:dashed] py-6 border-[rgba(0,0,0,0.12)] border-t">
            <div className="flex flex-wrap justify-between items-start gap-y-3 gap-x-3 caret-zinc-950 [color-scheme:light] mb-5">
              <div className="min-w-0 caret-zinc-950 [color-scheme:light]">
                <div className="text-zinc-500 font-semibold text-[11px] tracking-[1.98px] uppercase caret-zinc-500 [color-scheme:light]">
                  Paper Contract
                </div>
                <div className="text-zinc-500 leading-[28px] text-[14px] max-w-screen-md caret-zinc-500 [color-scheme:light] mt-2">
                  This is the current paper-facing contract the quest is
                  actually using: selected outline, experiment matrix, and
                  bundle control files.
                </div>
              </div>
            </div>
            <div className="text-zinc-500 leading-[28px] text-[14px] caret-zinc-500 [color-scheme:light] py-3">
              No selected paper contract is exposed in the current quest
              snapshot yet.
            </div>
          </section>
          <section className="[content-visibility:auto] [contain-intrinsic-width:720px] [contain-intrinsic-height:720px] [border-right-style:dashed] [border-bottom-style:dashed] [border-left-style:dashed] caret-zinc-950 [color-scheme:light] [border-top-style:dashed] py-6 border-[rgba(0,0,0,0.12)] border-t">
            <div className="flex flex-wrap justify-between items-start gap-y-3 gap-x-3 caret-zinc-950 [color-scheme:light] mb-5">
              <div className="min-w-0 caret-zinc-950 [color-scheme:light]">
                <div className="text-zinc-500 font-semibold text-[11px] tracking-[1.98px] uppercase caret-zinc-500 [color-scheme:light]">
                  Paper Lines
                </div>
                <div className="text-zinc-500 leading-[28px] text-[14px] max-w-screen-md caret-zinc-500 [color-scheme:light] mt-2">
                  Each serious paper-facing route should become a visible paper
                  line rather than hiding behind one quest-global paper panel.
                </div>
              </div>
            </div>
            <div className="min-w-0 caret-zinc-950 [color-scheme:light]">
              <div className="text-zinc-500 leading-[28px] text-[14px] caret-zinc-500 [color-scheme:light] py-3">
                No paper lines are exposed yet.
              </div>
            </div>
          </section>
          <section className="[content-visibility:auto] [contain-intrinsic-width:720px] [contain-intrinsic-height:720px] [border-right-style:dashed] [border-bottom-style:dashed] [border-left-style:dashed] caret-zinc-950 [color-scheme:light] [border-top-style:dashed] py-6 border-[rgba(0,0,0,0.12)] border-t">
            <div className="flex flex-wrap justify-between items-start gap-y-3 gap-x-3 caret-zinc-950 [color-scheme:light] mb-5">
              <div className="min-w-0 caret-zinc-950 [color-scheme:light]">
                <div className="text-zinc-500 font-semibold text-[11px] tracking-[1.98px] uppercase caret-zinc-500 [color-scheme:light]">
                  Evidence Ledger
                </div>
                <div className="text-zinc-500 leading-[28px] text-[14px] max-w-screen-md caret-zinc-500 [color-scheme:light] mt-2">
                  Paper-facing evidence items mirrored from main experiments and
                  analysis slices. This is the contract layer that should keep
                  completed results from disappearing before writing.
                </div>
              </div>
            </div>
            <div className="text-zinc-500 leading-[28px] text-[14px] caret-zinc-500 [color-scheme:light] py-3">
              No paper evidence ledger is exposed in the current quest snapshot
              yet.
            </div>
          </section>
          <section className="[content-visibility:auto] [contain-intrinsic-width:720px] [contain-intrinsic-height:720px] [border-right-style:dashed] [border-bottom-style:dashed] [border-left-style:dashed] caret-zinc-950 [color-scheme:light] [border-top-style:dashed] py-6 border-[rgba(0,0,0,0.12)] border-t">
            <div className="flex flex-wrap justify-between items-start gap-y-3 gap-x-3 caret-zinc-950 [color-scheme:light] mb-5">
              <div className="min-w-0 caret-zinc-950 [color-scheme:light]">
                <div className="text-zinc-500 font-semibold text-[11px] tracking-[1.98px] uppercase caret-zinc-500 [color-scheme:light]">
                  Analysis Inventory
                </div>
                <div className="text-zinc-500 leading-[28px] text-[14px] max-w-screen-md caret-zinc-500 [color-scheme:light] mt-2">
                  All detected paper-facing analysis campaigns and slice result
                  mirrors currently available under the quest.
                </div>
              </div>
            </div>
            <div className="text-zinc-500 leading-[28px] text-[14px] caret-zinc-500 [color-scheme:light] py-3">
              No analysis inventory is exposed in the current quest snapshot
              yet.
            </div>
          </section>
          <section className="[content-visibility:auto] [contain-intrinsic-width:720px] [contain-intrinsic-height:720px] [border-right-style:dashed] [border-bottom-style:dashed] [border-left-style:dashed] caret-zinc-950 [color-scheme:light] [border-top-style:dashed] py-6 border-[rgba(0,0,0,0.12)] border-t">
            <div className="flex flex-wrap justify-between items-start gap-y-3 gap-x-3 caret-zinc-950 [color-scheme:light] mb-5">
              <div className="min-w-0 caret-zinc-950 [color-scheme:light]">
                <div className="text-zinc-500 font-semibold text-[11px] tracking-[1.98px] uppercase caret-zinc-500 [color-scheme:light]">
                  Recent Progress
                </div>
                <div className="text-zinc-500 leading-[28px] text-[14px] max-w-screen-md caret-zinc-500 [color-scheme:light] mt-2">
                  Latest project messages, tool calls, artifacts, and runtime
                  runs in one linear view.
                </div>
              </div>
            </div>
            <div className="grid gap-y-8 gap-x-8 grid-cols-[minmax(0px,1.3fr)_minmax(0px,0.7fr)] caret-zinc-950 [color-scheme:light]">
              <div className="min-w-0 caret-zinc-950 [color-scheme:light]">
                <div className="text-zinc-500 leading-[28px] text-[14px] caret-zinc-500 [color-scheme:light] py-3">
                  No project activity yet.
                </div>
              </div>
              <div className="min-w-0 caret-zinc-950 [color-scheme:light]">
                <div className="min-w-0 caret-zinc-950 [color-scheme:light]">
                  <div className="text-zinc-500 leading-[28px] text-[14px] caret-zinc-500 [color-scheme:light] py-3">
                    Recent stage runs will appear here.
                  </div>
                </div>
              </div>
            </div>
          </section>
          <Component_7_1_2_6 />
        </div>
      </div>
    </div>
  );
}

export default Component_7_1_2;
