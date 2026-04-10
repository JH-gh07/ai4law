import Component_7_1_2_1_1 from './Component_7_1_2_1_1';

function Component_7_1_2_1() {
  return (
    <section
      className="[content-visibility:auto] [contain-intrinsic-width:560px] [contain-intrinsic-height:560px] caret-zinc-950 [color-scheme:light] pb-6"
      data-component-id="Component_7_1_2_1"
    >
      <Component_7_1_2_1_1 />
      <div className="text-zinc-500 leading-[20px] text-[14px] caret-zinc-500 [color-scheme:light] [border-top-style:dashed] [border-right-style:dashed] [border-bottom-style:dashed] [border-left-style:dashed] px-4 py-6 rounded-br-[24px] rounded-t-[24px] rounded-bl-[24px] border-[rgba(0,0,0,0.1)] border">
        Attach a baseline with recorded metrics to populate this section.
        Main-experiment traces will overlay after the first recorded result.
      </div>
    </section>
  );
}

export default Component_7_1_2_1;
