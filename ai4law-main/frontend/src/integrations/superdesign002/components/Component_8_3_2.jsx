function Component_8_3_2() {
  return (
    <div
      className="relative caret-zinc-950 [color-scheme:light]"
      data-component-id="Component_8_3_2"
    >
      <div className="bg-[rgba(252,250,246,0.96)] relative overflow-x-hidden overflow-y-hidden shadow-[rgba(0,0,0,0)_0px_0px_0px_0px,rgba(0,0,0,0)_0px_0px_0px_0px,rgba(24,28,32,0.28)_0px_22px_52px_-40px] backdrop-blur-xl caret-zinc-950 [color-scheme:light] rounded-br-[18px] rounded-t-[18px] rounded-bl-[18px] border-[rgba(0,0,0,0.08)] border">
        <textarea
          rows="2"
          placeholder="发送备注、回复决策，或使用 /status /approve /pause /resume …"
          className="bg-[rgba(0,0,0,0)] leading-[1.7] text-[12.5px] w-full h-[115px] block overflow-y-hidden outline outline-2 outline-[rgba(0,0,0,0)] outline-offset-2 caret-zinc-950 [color-scheme:light] resize-none pl-4 pr-[174px] pt-4 pb-14"
        ></textarea>
        <div className="absolute flex justify-between items-center caret-zinc-950 [color-scheme:light] pb-3 px-4 top-auto bottom-0 inset-x-0">
          <div className="text-zinc-500 leading-[20px] text-[12px] min-w-0 caret-zinc-500 [color-scheme:light] pr-4">
            <span
              title="Enter 发送 · Shift+Enter 换行"
              className="text-ellipsis [white-space-collapse:collapse] [text-wrap-mode:nowrap] block overflow-x-hidden overflow-y-hidden caret-zinc-500 [color-scheme:light]"
            >
              Enter 发送 · Shift+…
            </span>
          </div>
          <div className="flex shrink-0 items-center gap-y-2 gap-x-2 caret-zinc-950 [color-scheme:light]">
            <button
              type="button"
              className="bg-[rgba(255,255,255,0.82)] font-medium text-[12px] h-8 flex items-center caret-zinc-950 [color-scheme:light] [appearance:button] px-3 py-0 rounded-br-full rounded-t-full rounded-bl-full border-[rgba(0,0,0,0.08)] border"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="rgb(9, 9, 11)"
                strokeWidth="2px"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
                className="text-center align-middle w-3.5 h-3.5 block overflow-x-hidden overflow-y-hidden fill-none stroke-zinc-950 stroke-[2px] [stroke-linecap:round] [stroke-linejoin:round] caret-zinc-950 [color-scheme:light] mr-1.5"
                data-svg-size="635"
              >
                <rect
                  width="18"
                  height="18"
                  x="3"
                  y="3"
                  rx="2"
                  className="w-[18px] h-[18px] inline fill-none stroke-zinc-950 stroke-[2px] [stroke-linecap:round] [stroke-linejoin:round] caret-zinc-950 [color-scheme:light]"
                ></rect>
              </svg>
              停止
            </button>
            <button
              type="button"
              disabled
              className="bg-[#2f3437] text-white font-medium text-[12px] h-8 flex items-center opacity-50 caret-white [color-scheme:light] [appearance:button] px-3 py-0 rounded-br-full rounded-t-full rounded-bl-full"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="rgb(255, 255, 255)"
                strokeWidth="2px"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
                className="text-center align-middle w-3.5 h-3.5 block overflow-x-hidden overflow-y-hidden fill-none stroke-white stroke-[2px] [stroke-linecap:round] [stroke-linejoin:round] caret-white [color-scheme:light] mr-1.5"
                data-svg-size="743"
              >
                <path
                  d="m5 12 7-7 7 7"
                  className="inline fill-none stroke-white stroke-[2px] [stroke-linecap:round] [stroke-linejoin:round] caret-white [color-scheme:light]"
                ></path>
                <path
                  d="M12 19V5"
                  className="inline fill-none stroke-white stroke-[2px] [stroke-linecap:round] [stroke-linejoin:round] caret-white [color-scheme:light]"
                ></path>
              </svg>
              发送
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Component_8_3_2;
