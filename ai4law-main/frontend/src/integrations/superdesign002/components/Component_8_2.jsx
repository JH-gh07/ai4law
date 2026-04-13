import Component_8_2_1 from './Component_8_2_1';

function Component_8_2() {
  return (
    <div
      role="toolbar"
      aria-label="Copilot 控件"
      className="relative z-[3] flex shrink-0 items-center gap-y-2 gap-x-2 caret-[#2d2a26] [color-scheme:light] select-none"
      data-component-id="Component_8_2"
    >
      <Component_8_2_1 />
      <button
        type="button"
        aria-label="隐藏 Copilot"
        className="bg-[rgba(255,255,255,0.74)] text-[#7e8b97] text-[16px] w-8 h-8 flex justify-center items-center caret-[#7e8b97] [color-scheme:light] select-none [appearance:button] p-0 rounded-br-[10px] rounded-t-[10px] rounded-bl-[10px] border-[rgba(0,0,0,0.08)] border"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="rgb(126, 139, 151)"
          strokeWidth="2px"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
          className="text-center align-middle w-4 h-4 block overflow-x-hidden overflow-y-hidden fill-none stroke-[#7e8b97] stroke-[2px] [stroke-linecap:round] [stroke-linejoin:round] caret-[#7e8b97] [color-scheme:light] select-none"
          data-svg-size="791"
        >
          <path
            d="M18 6 6 18"
            className="inline fill-none stroke-[#7e8b97] stroke-[2px] [stroke-linecap:round] [stroke-linejoin:round] caret-[#7e8b97] [color-scheme:light] select-none"
          ></path>
          <path
            d="m6 6 12 12"
            className="inline fill-none stroke-[#7e8b97] stroke-[2px] [stroke-linecap:round] [stroke-linejoin:round] caret-[#7e8b97] [color-scheme:light] select-none"
          ></path>
        </svg>
      </button>
    </div>
  );
}

export default Component_8_2;
