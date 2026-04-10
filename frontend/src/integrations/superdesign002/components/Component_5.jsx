import Component_5_1 from './Component_5_1';
import Component_5_2 from './Component_5_2';

function Component_5() {
  return (
    <div
      className="min-h-0 flex flex-col grow basis-[0%] caret-[rgba(242,238,232,0.72)] [color-scheme:light]"
      data-component-id="Component_5"
    >
      <div className="flex items-center gap-y-3 gap-x-3 caret-[rgba(242,238,232,0.72)] [color-scheme:light] px-4 py-2 border-[rgba(255,255,255,0.08)] border-b">
        <div className="flex items-center gap-y-0.5 gap-x-0.5 caret-[rgba(242,238,232,0.72)] [color-scheme:light] ml-auto">
          <button
            title="新建文件"
            aria-label="新建文件"
            type="button"
            className="bg-[rgba(0,0,0,0)] leading-[20px] font-medium text-[14px] [white-space-collapse:collapse] [text-wrap-mode:nowrap] w-7 h-7 flex justify-center items-center caret-[rgba(242,238,232,0.72)] [color-scheme:light] [appearance:button] p-0 rounded-br-[6px] rounded-t-[6px] rounded-bl-[6px]"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="rgba(242, 238, 232, 0.72)"
              strokeWidth="2px"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
              className="text-center [text-wrap-mode:nowrap] align-middle w-3.5 h-3.5 block overflow-x-hidden overflow-y-hidden fill-none stroke-[rgba(242,238,232,0.72)] stroke-[2px] [stroke-linecap:round] [stroke-linejoin:round] caret-[rgba(242,238,232,0.72)] [color-scheme:light]"
              data-svg-size="1427"
            >
              <path
                d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"
                className="[text-wrap-mode:nowrap] inline fill-none stroke-[rgba(242,238,232,0.72)] stroke-[2px] [stroke-linecap:round] [stroke-linejoin:round] caret-[rgba(242,238,232,0.72)] [color-scheme:light]"
              ></path>
              <path
                d="M14 2v4a2 2 0 0 0 2 2h4"
                className="[text-wrap-mode:nowrap] inline fill-none stroke-[rgba(242,238,232,0.72)] stroke-[2px] [stroke-linecap:round] [stroke-linejoin:round] caret-[rgba(242,238,232,0.72)] [color-scheme:light]"
              ></path>
              <path
                d="M9 15h6"
                className="[text-wrap-mode:nowrap] inline fill-none stroke-[rgba(242,238,232,0.72)] stroke-[2px] [stroke-linecap:round] [stroke-linejoin:round] caret-[rgba(242,238,232,0.72)] [color-scheme:light]"
              ></path>
              <path
                d="M12 18v-6"
                className="[text-wrap-mode:nowrap] inline fill-none stroke-[rgba(242,238,232,0.72)] stroke-[2px] [stroke-linecap:round] [stroke-linejoin:round] caret-[rgba(242,238,232,0.72)] [color-scheme:light]"
              ></path>
            </svg>
          </button>
          <button
            title="新建文件夹"
            aria-label="新建文件夹"
            type="button"
            className="bg-[rgba(0,0,0,0)] leading-[20px] font-medium text-[14px] [white-space-collapse:collapse] [text-wrap-mode:nowrap] w-7 h-7 flex justify-center items-center caret-[rgba(242,238,232,0.72)] [color-scheme:light] [appearance:button] p-0 rounded-br-[6px] rounded-t-[6px] rounded-bl-[6px]"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="rgba(242, 238, 232, 0.72)"
              strokeWidth="2px"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
              className="text-center [text-wrap-mode:nowrap] align-middle w-3.5 h-3.5 block overflow-x-hidden overflow-y-hidden fill-none stroke-[rgba(242,238,232,0.72)] stroke-[2px] [stroke-linecap:round] [stroke-linejoin:round] caret-[rgba(242,238,232,0.72)] [color-scheme:light]"
              data-svg-size="1252"
            >
              <path
                d="M12 10v6"
                className="[text-wrap-mode:nowrap] inline fill-none stroke-[rgba(242,238,232,0.72)] stroke-[2px] [stroke-linecap:round] [stroke-linejoin:round] caret-[rgba(242,238,232,0.72)] [color-scheme:light]"
              ></path>
              <path
                d="M9 13h6"
                className="[text-wrap-mode:nowrap] inline fill-none stroke-[rgba(242,238,232,0.72)] stroke-[2px] [stroke-linecap:round] [stroke-linejoin:round] caret-[rgba(242,238,232,0.72)] [color-scheme:light]"
              ></path>
              <path
                d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"
                className="[text-wrap-mode:nowrap] inline fill-none stroke-[rgba(242,238,232,0.72)] stroke-[2px] [stroke-linecap:round] [stroke-linejoin:round] caret-[rgba(242,238,232,0.72)] [color-scheme:light]"
              ></path>
            </svg>
          </button>
          <button
            title="上传文件"
            aria-label="上传文件"
            type="button"
            className="bg-[rgba(0,0,0,0)] leading-[20px] font-medium text-[14px] [white-space-collapse:collapse] [text-wrap-mode:nowrap] w-7 h-7 flex justify-center items-center caret-[rgba(242,238,232,0.72)] [color-scheme:light] [appearance:button] p-0 rounded-br-[6px] rounded-t-[6px] rounded-bl-[6px]"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="rgba(242, 238, 232, 0.72)"
              strokeWidth="2px"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
              className="text-center [text-wrap-mode:nowrap] align-middle w-3.5 h-3.5 block overflow-x-hidden overflow-y-hidden fill-none stroke-[rgba(242,238,232,0.72)] stroke-[2px] [stroke-linecap:round] [stroke-linejoin:round] caret-[rgba(242,238,232,0.72)] [color-scheme:light]"
              data-svg-size="1181"
            >
              <path
                d="M12 3v12"
                className="[text-wrap-mode:nowrap] inline fill-none stroke-[rgba(242,238,232,0.72)] stroke-[2px] [stroke-linecap:round] [stroke-linejoin:round] caret-[rgba(242,238,232,0.72)] [color-scheme:light]"
              ></path>
              <path
                d="m17 8-5-5-5 5"
                className="[text-wrap-mode:nowrap] inline fill-none stroke-[rgba(242,238,232,0.72)] stroke-[2px] [stroke-linecap:round] [stroke-linejoin:round] caret-[rgba(242,238,232,0.72)] [color-scheme:light]"
              ></path>
              <path
                d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"
                className="[text-wrap-mode:nowrap] inline fill-none stroke-[rgba(242,238,232,0.72)] stroke-[2px] [stroke-linecap:round] [stroke-linejoin:round] caret-[rgba(242,238,232,0.72)] [color-scheme:light]"
              ></path>
            </svg>
          </button>
          <button
            title="显示 .files"
            aria-label="显示 .files"
            type="button"
            className="bg-[rgba(0,0,0,0)] leading-[20px] font-medium text-[14px] [white-space-collapse:collapse] [text-wrap-mode:nowrap] w-7 h-7 flex justify-center items-center caret-[rgba(242,238,232,0.72)] [color-scheme:light] [appearance:button] p-0 rounded-br-[6px] rounded-t-[6px] rounded-bl-[6px]"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="rgba(242, 238, 232, 0.72)"
              strokeWidth="2px"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="text-center [text-wrap-mode:nowrap] align-middle w-3.5 h-3.5 block overflow-x-hidden overflow-y-hidden fill-none stroke-[rgba(242,238,232,0.72)] stroke-[2px] [stroke-linecap:round] [stroke-linejoin:round] caret-[rgba(242,238,232,0.72)] [color-scheme:light]"
              data-svg-size="1479"
            >
              <path
                d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"
                className="[text-wrap-mode:nowrap] inline fill-none stroke-[rgba(242,238,232,0.72)] stroke-[2px] [stroke-linecap:round] [stroke-linejoin:round] caret-[rgba(242,238,232,0.72)] [color-scheme:light]"
              ></path>
              <polyline
                points="14 2 14 8 20 8"
                className="[text-wrap-mode:nowrap] inline fill-none stroke-[rgba(242,238,232,0.72)] stroke-[2px] [stroke-linecap:round] [stroke-linejoin:round] caret-[rgba(242,238,232,0.72)] [color-scheme:light]"
              ></polyline>
              <circle
                cx="10"
                cy="15"
                r="1.5"
                fill="rgba(242, 238, 232, 0.72)"
                stroke="none"
                className="[text-wrap-mode:nowrap] inline fill-[rgba(242,238,232,0.72)] stroke-[2px] [stroke-linecap:round] [stroke-linejoin:round] caret-[rgba(242,238,232,0.72)] [color-scheme:light]"
              ></circle>
              <line
                x1="4"
                y1="20"
                x2="20"
                y2="4"
                className="[text-wrap-mode:nowrap] inline fill-none stroke-[rgba(242,238,232,0.72)] stroke-[2px] [stroke-linecap:round] [stroke-linejoin:round] caret-[rgba(242,238,232,0.72)] [color-scheme:light]"
              ></line>
            </svg>
          </button>
          <button
            title="刷新"
            aria-label="刷新"
            type="button"
            className="bg-[rgba(0,0,0,0)] leading-[20px] font-medium text-[14px] [white-space-collapse:collapse] [text-wrap-mode:nowrap] w-7 h-7 flex justify-center items-center caret-[rgba(242,238,232,0.72)] [color-scheme:light] [appearance:button] p-0 rounded-br-[6px] rounded-t-[6px] rounded-bl-[6px]"
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
              className="text-white text-center [text-wrap-mode:nowrap] align-middle w-3.5 h-3.5 block overflow-x-hidden overflow-y-hidden fill-none stroke-white stroke-[2px] [stroke-linecap:round] [stroke-linejoin:round] caret-white [color-scheme:light]"
              data-svg-size="1264"
            >
              <path
                d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"
                className="[text-wrap-mode:nowrap] inline fill-none stroke-white stroke-[2px] [stroke-linecap:round] [stroke-linejoin:round] caret-white [color-scheme:light]"
              ></path>
              <path
                d="M21 3v5h-5"
                className="[text-wrap-mode:nowrap] inline fill-none stroke-white stroke-[2px] [stroke-linecap:round] [stroke-linejoin:round] caret-white [color-scheme:light]"
              ></path>
              <path
                d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"
                className="[text-wrap-mode:nowrap] inline fill-none stroke-white stroke-[2px] [stroke-linecap:round] [stroke-linejoin:round] caret-white [color-scheme:light]"
              ></path>
              <path
                d="M8 16H3v5"
                className="[text-wrap-mode:nowrap] inline fill-none stroke-white stroke-[2px] [stroke-linecap:round] [stroke-linejoin:round] caret-white [color-scheme:light]"
              ></path>
            </svg>
          </button>
        </div>
      </div>
      <div className="min-h-0 flex overflow-x-hidden overflow-y-hidden flex-col grow basis-[0%] caret-[rgba(242,238,232,0.72)] [color-scheme:light]">
        <div
          role="tabpanel"
          aria-hidden="false"
          className="min-h-0 flex overflow-x-hidden overflow-y-hidden flex-col grow basis-[0%] caret-[rgba(242,238,232,0.72)] [color-scheme:light]"
        >
          <Component_5_1 />
        </div>
        <div
          role="tabpanel"
          aria-hidden="true"
          className="min-h-0 hidden overflow-x-hidden overflow-y-hidden grow basis-[0%] caret-[rgba(242,238,232,0.72)] [color-scheme:light]"
        >
          <Component_5_2 />
        </div>
      </div>
    </div>
  );
}

export default Component_5;
