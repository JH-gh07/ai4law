function Component_1({ appName = 'AI4Law', workspaceName = '工作台', onBackToTasks }) {
  return (
    <div
      className="text-gray-800 font-semibold text-[15.2px] flex items-center gap-y-2.5 gap-x-2.5 caret-gray-800 [color-scheme:light] mr-3"
      data-component-id="Component_1"
    >
      <div className="flex items-center gap-y-1 gap-x-1 caret-gray-800 [color-scheme:light] mr-[7px]">
        <button
          aria-label="工作区布局"
          className="bg-[rgba(47,52,55,0.1)] text-[#2f3437] w-8 h-8 flex justify-center items-center shadow-[rgba(47,52,55,0.22)_0px_0px_0px_1px_inset,rgba(0,0,0,0.06)_0px_1px_2px_0px] caret-[#2f3437] [color-scheme:light] [appearance:button] p-0 rounded-br-[8px] rounded-t-[8px] rounded-bl-[8px] hover:bg-[rgba(0,0,0,0.05)] hover:text-[color:var(--text-main)] hover:bg-[initial] hover:[background-repeat:initial] hover:[background-clip:initial] hover:[background-origin:initial] hover:[background-attachment:initial] disabled:opacity-[0.56] group"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2px"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="text-center align-middle w-[18px] h-[18px] block overflow-x-hidden overflow-y-hidden fill-none stroke-[#2f3437] stroke-[2px] [stroke-linecap:round] [stroke-linejoin:round] caret-[#2f3437] [color-scheme:light]"
            aria-hidden="true"
          >
            <rect x="3" y="3" width="7" height="7"></rect>
            <rect x="14" y="3" width="7" height="7"></rect>
            <rect x="3" y="14" width="7" height="7"></rect>
            <rect x="14" y="14" width="7" height="7"></rect>
          </svg>
        </button>
        <button
          type="button"
          aria-label="返回任务空间"
          onClick={() => onBackToTasks?.()}
          className="bg-[rgba(0,0,0,0)] text-[#6f6b66] w-8 h-8 flex justify-center items-center caret-[#6f6b66] [color-scheme:light] [appearance:button] p-0 rounded-br-[8px] rounded-t-[8px] rounded-bl-[8px] hover:bg-[rgba(0,0,0,0.05)] hover:text-[color:var(--text-main)] hover:bg-[initial] hover:[background-repeat:initial] hover:[background-clip:initial] hover:[background-origin:initial] hover:[background-attachment:initial] disabled:opacity-[0.56] group"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="rgb(111, 107, 102)"
            strokeWidth="2px"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
            className="text-center align-middle w-4 h-4 block overflow-x-hidden overflow-y-hidden fill-none stroke-[#6f6b66] stroke-[2px] [stroke-linecap:round] [stroke-linejoin:round] caret-[#6f6b66] [color-scheme:light]"
            data-svg-size="592"
          >
            <path
              d="m15 18-6-6 6-6"
              className="inline fill-none stroke-[#6f6b66] stroke-[2px] [stroke-linecap:round] [stroke-linejoin:round] caret-[#6f6b66] [color-scheme:light]"
            ></path>
          </svg>
        </button>
      </div>
      <div className="flex items-center caret-gray-800 [color-scheme:light]">
        <button
          type="button"
          aria-label={appName}
          className="bg-[rgba(0,0,0,0)] flex items-center gap-y-2 gap-x-2 caret-gray-800 [color-scheme:light] [appearance:button] pl-0.5 pr-2.5 py-0.5 rounded-br-[999px] rounded-t-[999px] rounded-bl-[999px] border-[rgba(0,0,0,0)] border hover:bg-[rgba(0,0,0,0.04)] hover:bg-[initial] hover:[background-repeat:initial] hover:[background-clip:initial] hover:[background-origin:initial] hover:[background-attachment:initial] hover:border-[rgba(0,0,0,0.06)]"
        >
          <span className="text-[13.6px] text-center text-ellipsis [white-space-collapse:collapse] [text-wrap-mode:nowrap] max-w-[140px] block overflow-x-hidden overflow-y-hidden caret-gray-800 [color-scheme:light]">
            {appName}
          </span>
        </button>
      </div>
      <span className="text-[#6f6b66] block caret-[#6f6b66] [color-scheme:light] mx-2">
        /
      </span>
      <button
        type="button"
        title={workspaceName}
        className="bg-[rgba(0,0,0,0)] min-w-0 max-w-[233.836px] block caret-gray-800 [color-scheme:light] [appearance:button] p-0"
      >
        <span className="text-center text-ellipsis [white-space-collapse:collapse] [text-wrap-mode:nowrap] w-full block overflow-x-hidden overflow-y-hidden caret-gray-800 [color-scheme:light]">
          {workspaceName}
        </span>
      </button>
    </div>
  );
}

export default Component_1;
