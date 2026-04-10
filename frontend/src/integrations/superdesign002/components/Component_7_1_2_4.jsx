import Component_7_1_2_4_1 from './Component_7_1_2_4_1';

function Component_7_1_2_4() {
  return (
    <section
      className="[content-visibility:auto] [contain-intrinsic-width:720px] [contain-intrinsic-height:720px] [border-right-style:dashed] [border-bottom-style:dashed] [border-left-style:dashed] caret-zinc-950 [color-scheme:light] [border-top-style:dashed] py-6 border-[rgba(0,0,0,0.12)] border-t"
      data-component-id="Component_7_1_2_4"
    >
      <div className="flex flex-wrap justify-between items-start gap-y-3 gap-x-3 caret-zinc-950 [color-scheme:light] mb-5">
        <div className="min-w-0 caret-zinc-950 [color-scheme:light]">
          <div className="text-zinc-500 font-semibold text-[11px] tracking-[1.98px] uppercase caret-zinc-500 [color-scheme:light]">
            Operational Status
          </div>
          <div className="text-zinc-500 leading-[28px] text-[14px] max-w-screen-md caret-zinc-500 [color-scheme:light] mt-2">
            Details concentrates the same high-signal project state that a quick
            /status-style check should expose.
          </div>
        </div>
      </div>
      <div className="grid gap-y-8 gap-x-8 grid-cols-[minmax(0px,1.35fr)_minmax(0px,0.85fr)] caret-zinc-950 [color-scheme:light]">
        <div className="min-w-0 caret-zinc-950 [color-scheme:light]">
          <div className="caret-zinc-950 [color-scheme:light]">
            <div className="grid gap-y-2 gap-x-2 grid-cols-[150px_minmax(0px,1fr)] caret-zinc-950 [color-scheme:light] py-3">
              <div className="text-zinc-500 text-[11px] tracking-[1.76px] uppercase caret-zinc-500 [color-scheme:light]">
                Runtime state
              </div>
              <div className="leading-[28px] text-[14px] caret-zinc-950 [color-scheme:light]">
                running
              </div>
            </div>
            <div className="[border-right-style:dashed] [border-bottom-style:dashed] [border-left-style:dashed] grid gap-y-2 gap-x-2 grid-cols-[150px_minmax(0px,1fr)] caret-zinc-950 [color-scheme:light] [border-top-style:dashed] py-3 border-[rgba(0,0,0,0.1)] border-t">
              <div className="text-zinc-500 text-[11px] tracking-[1.76px] uppercase caret-zinc-500 [color-scheme:light]">
                Pending work
              </div>
              <div className="leading-[28px] text-[14px] caret-zinc-950 [color-scheme:light]">
                0 pending decisions · 0 queued user messages
              </div>
            </div>
            <div className="[border-right-style:dashed] [border-bottom-style:dashed] [border-left-style:dashed] grid gap-y-2 gap-x-2 grid-cols-[150px_minmax(0px,1fr)] caret-zinc-950 [color-scheme:light] [border-top-style:dashed] py-3 border-[rgba(0,0,0,0.1)] border-t">
              <div className="text-zinc-500 text-[11px] tracking-[1.76px] uppercase caret-zinc-500 [color-scheme:light]">
                Interaction
              </div>
              <div className="leading-[28px] text-[14px] caret-zinc-950 [color-scheme:light]">
                Active interaction progress-8327805f
              </div>
            </div>
            <div className="[border-right-style:dashed] [border-bottom-style:dashed] [border-left-style:dashed] grid gap-y-2 gap-x-2 grid-cols-[150px_minmax(0px,1fr)] caret-zinc-950 [color-scheme:light] [border-top-style:dashed] py-3 border-[rgba(0,0,0,0.1)] border-t">
              <div className="text-zinc-500 text-[11px] tracking-[1.76px] uppercase caret-zinc-500 [color-scheme:light]">
                Latest delivery
              </div>
              <div className="leading-[28px] text-[14px] caret-zinc-950 [color-scheme:light]">
                No mailbox delivery recorded yet
              </div>
            </div>
          </div>
        </div>
        <Component_7_1_2_4_1 />
      </div>
    </section>
  );
}

export default Component_7_1_2_4;
