import Component_7_1_2_5_1 from './Component_7_1_2_5_1';

function Component_7_1_2_5() {
  return (
    <section
      className="[content-visibility:auto] [contain-intrinsic-width:720px] [contain-intrinsic-height:720px] [border-right-style:dashed] [border-bottom-style:dashed] [border-left-style:dashed] caret-zinc-950 [color-scheme:light] [border-top-style:dashed] py-6 border-[rgba(0,0,0,0.12)] border-t"
      data-component-id="Component_7_1_2_5"
    >
      <div className="flex flex-wrap justify-between items-start gap-y-3 gap-x-3 caret-zinc-950 [color-scheme:light] mb-5">
        <div className="min-w-0 caret-zinc-950 [color-scheme:light]">
          <div className="text-zinc-500 font-semibold text-[11px] tracking-[1.98px] uppercase caret-zinc-500 [color-scheme:light]">
            Optimization Frontier
          </div>
          <div className="text-zinc-500 leading-[28px] text-[14px] max-w-screen-md caret-zinc-500 [color-scheme:light] mt-2">
            No durable optimization line or candidate pool is active, so there
            is no meaningful frontier to continue automatically.
          </div>
        </div>
      </div>
      <div className="grid gap-y-8 gap-x-8 grid-cols-[minmax(0px,1.1fr)_minmax(0px,0.9fr)] caret-zinc-950 [color-scheme:light]">
        <Component_7_1_2_5_1 />
        <div className="min-w-0 caret-zinc-950 [color-scheme:light]">
          <div className="min-w-0 caret-zinc-950 [color-scheme:light]">
            <div className="flex justify-between items-center gap-y-3 gap-x-3 caret-zinc-950 [color-scheme:light] mb-2">
              <div className="min-w-0 flex items-center gap-y-3 gap-x-3 caret-zinc-950 [color-scheme:light]">
                <div className="text-zinc-500 font-semibold text-[11px] tracking-[1.76px] uppercase caret-zinc-500 [color-scheme:light]">
                  Implementation Candidates
                </div>
              </div>
            </div>
            <div className="text-zinc-500 leading-[28px] text-[14px] caret-zinc-500 [color-scheme:light] py-3">
              No implementation-level optimization candidates are recorded yet.
            </div>
          </div>
          <div className="min-w-0 caret-zinc-950 [color-scheme:light] mt-8">
            <div className="text-zinc-500 leading-[28px] text-[14px] caret-zinc-500 [color-scheme:light] py-3">
              No stagnant lines detected yet.
            </div>
          </div>
          <div className="min-w-0 caret-zinc-950 [color-scheme:light] mt-8">
            <div className="flex justify-between items-center gap-y-3 gap-x-3 caret-zinc-950 [color-scheme:light] mb-2">
              <div className="min-w-0 flex items-center gap-y-3 gap-x-3 caret-zinc-950 [color-scheme:light]">
                <div className="text-zinc-500 font-semibold text-[11px] tracking-[1.76px] uppercase caret-zinc-500 [color-scheme:light]">
                  Fusion Opportunities
                </div>
              </div>
            </div>
            <div className="text-zinc-500 leading-[28px] text-[14px] caret-zinc-500 [color-scheme:light] py-3">
              No fusion opportunities are currently exposed.
            </div>
          </div>
          <div className="min-w-0 caret-zinc-950 [color-scheme:light] mt-8">
            <div className="text-zinc-500 font-semibold text-[11px] tracking-[1.76px] uppercase caret-zinc-500 [color-scheme:light] mb-2">
              Recommended Next Actions
            </div>
            <div className="caret-zinc-950 [color-scheme:light]">
              <div className="leading-[28px] text-[14px] caret-zinc-950 [color-scheme:light]">
                Record a stop or park decision before closing the optimization
                loop.
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export default Component_7_1_2_5;
