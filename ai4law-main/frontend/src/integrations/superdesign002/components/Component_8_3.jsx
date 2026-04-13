import Component_8_3_1 from './Component_8_3_1';
import Component_8_3_2 from './Component_8_3_2';

function Component_8_3() {
  return (
    <div
      className="min-h-0 relative z-10 flex overflow-x-hidden overflow-y-hidden flex-col grow basis-[0%] caret-zinc-950 [color-scheme:light] pt-1.5 pb-3 px-3.5"
      data-component-id="Component_8_3"
    >
      <div className="h-full min-h-0 flex flex-col caret-zinc-950 [color-scheme:light]">
        <div className="h-full min-h-0 flex flex-col caret-zinc-950 [color-scheme:light]">
          <div className="text-[rgba(113,113,122,0.9)] leading-[20px] text-[12px] caret-[rgba(113,113,122,0.9)] [color-scheme:light] pt-3 px-4">
            Studio 轨迹已就绪
          </div>
          <div className="min-h-0 flex overflow-x-hidden overflow-y-hidden flex-col grow basis-[0%] caret-zinc-950 [color-scheme:light]">
            <Component_8_3_1 />
          </div>
          <div className="caret-zinc-950 [color-scheme:light] px-4 py-3">
            <Component_8_3_2 />
          </div>
        </div>
      </div>
    </div>
  );
}

export default Component_8_3;
