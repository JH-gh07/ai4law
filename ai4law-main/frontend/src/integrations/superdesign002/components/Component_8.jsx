import Component_8_1 from './Component_8_1';
import Component_8_2 from './Component_8_2';
import Component_8_3 from './Component_8_3';

function Component_8() {
  return (
    <div
      aria-hidden="false"
      aria-label="Copilot 停靠面板"
      className="[--ds-copilot-inset:4px] [--ds-copilot-gap:25px] block absolute z-[80] caret-zinc-950 [color-scheme:light] pointer-events-none inset-1"
      data-component-id="Component_8"
    >
      <div className="w-[400px] min-w-0 max-w-full absolute z-[90] flex flex-col [filter:drop-shadow(rgba(32,40,52,0.16)_0px_16px_34px)] will-change-transform caret-zinc-950 [color-scheme:light] rounded-br-[18px] rounded-t-[18px] rounded-bl-[18px] left-[824px] right-auto inset-y-1.5 group">
        <div className="[--ds-glare-x:58.2305908203125px] [--ds-glare-y:304.89056396484375px] w-full h-full relative overflow-x-hidden overflow-y-hidden caret-zinc-950 [color-scheme:light] rounded-br-[18px] rounded-t-[18px] rounded-bl-[18px] group">
          <div
            aria-hidden="true"
            className="absolute opacity-0 mix-blend-soft-light caret-zinc-950 [color-scheme:light] pointer-events-none inset-0"
            data-style-id="style-6-1775848859187"
          ></div>
          <div
            className="[--ds-spotlight-color:rgba(159,177,194,0.24)] [--ds-spotlight-x:58px] [--ds-spotlight-y:304px] w-full h-full min-h-0 relative flex overflow-x-hidden overflow-y-hidden flex-col [background-position-x:0%,0%,0%] [background-position-y:0%,0%,0%] [background-repeat:repeat,repeat,repeat] shadow-[rgba(45,42,38,0.18)_0px_24px_60px_0px,rgba(199,173,150,0.2)_0px_0px_0px_0.75px] backdrop-blur-[22px] backdrop-saturate-[1.3] [transform:translate3d(0px,0px,0px)] caret-zinc-950 [color-scheme:light] rounded-br-[18px] rounded-t-[18px] rounded-bl-[18px] border-[rgba(45,42,38,0.14)] border hover:opacity-100"
            data-style-id="style-7-1775848859188"
          >
            <div
              aria-hidden="true"
              className="absolute [background-position-x:24px] [background-position-y:-18px] bg-[260px_260px] opacity-[0.06] caret-zinc-950 [color-scheme:light] pointer-events-none inset-0"
              data-style-id="style-8-1775848859188"
            ></div>
            <div className="w-full h-full min-h-0 relative flex flex-col isolate caret-zinc-950 [color-scheme:light] rounded-br-[18px] rounded-t-[18px] rounded-bl-[18px]">
              <div className="text-[#2d2a26] relative z-40 flex justify-between items-center gap-y-3 gap-x-3 caret-[#2d2a26] [color-scheme:light] select-none mt-3 mb-2.5 mx-3.5 px-3 py-2">
                <Component_8_1 />
                <Component_8_2 />
              </div>
              <div className="min-h-0 relative flex overflow-x-hidden overflow-y-hidden flex-col grow basis-[0%] caret-zinc-950 [color-scheme:light]">
                <Component_8_3 />
              </div>
              <div
                role="separator"
                aria-label="调整 Copilot 大小"
                tabIndex="0"
                className="w-3 absolute z-30 caret-zinc-950 [color-scheme:light] left-0 right-auto inset-y-3"
              ></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Component_8;
