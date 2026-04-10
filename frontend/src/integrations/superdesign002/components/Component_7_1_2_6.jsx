import Component_7_1_2_6_1 from './Component_7_1_2_6_1';
import Component_7_1_2_6_2 from './Component_7_1_2_6_2';

function Component_7_1_2_6() {
  return (
    <section
      className="[content-visibility:auto] [contain-intrinsic-width:720px] [contain-intrinsic-height:720px] [border-right-style:dashed] [border-bottom-style:dashed] [border-left-style:dashed] caret-zinc-950 [color-scheme:light] [border-top-style:dashed] py-6 border-[rgba(0,0,0,0.12)] border-t"
      data-component-id="Component_7_1_2_6"
    >
      <div className="flex flex-wrap justify-between items-start gap-y-3 gap-x-3 caret-zinc-950 [color-scheme:light] mb-5">
        <div className="min-w-0 caret-zinc-950 [color-scheme:light]">
          <div className="text-zinc-500 font-semibold text-[11px] tracking-[1.98px] uppercase caret-zinc-500 [color-scheme:light]">
            Working Set
          </div>
          <div className="text-zinc-500 leading-[28px] text-[14px] max-w-screen-md caret-zinc-500 [color-scheme:light] mt-2">
            High-frequency project materials: changed files, documents, memory,
            and durable artifact outputs.
          </div>
        </div>
      </div>
      <div className="grid gap-y-8 gap-x-8 grid-cols-[repeat(2,minmax(0px,1fr))] caret-zinc-950 [color-scheme:light]">
        <Component_7_1_2_6_1 />
        <Component_7_1_2_6_2 />
      </div>
    </section>
  );
}

export default Component_7_1_2_6;
