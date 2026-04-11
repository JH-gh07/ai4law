const DEFAULT_TABS = [
  { id: 'details', label: 'Details' },
  { id: 'canvas', label: 'Canvas' },
  { id: 'report', label: 'Report' },
  { id: 'terminal', label: 'Terminal' }
];

function Component_2({ tabs = DEFAULT_TABS, activeTabId = 'details', onSelectTab }) {
  return (
    <div
      className="min-w-0 flex grow basis-[0%] items-center caret-zinc-950 [color-scheme:light]"
      data-component-id="Component_2"
    >
      <div className="w-full min-w-0 flex items-center gap-y-2 gap-x-2 caret-zinc-950 [color-scheme:light]">
        <div className="min-w-0 grow basis-[0%] caret-zinc-950 [color-scheme:light]">
          <div className="w-full min-w-0 flex items-stretch caret-zinc-950 [color-scheme:light] group">
            <div
              role="tablist"
              aria-label="工作区"
              className="min-w-0 flex overflow-y-hidden grow basis-[0%] items-stretch gap-y-1 gap-x-1 caret-zinc-950 [color-scheme:light] mt-px"
            >
              {tabs.map((tab) => {
                const active = tab.id === activeTabId;
                return (
                  <button
                    key={tab.id}
                    type="button"
                    role="tab"
                    aria-selected={active}
                    title={tab.label}
                    onClick={() => onSelectTab?.(tab.id)}
                    className={`text-gray-800 text-[12.8px] h-[26px] min-w-[140px] max-w-[420px] flex grow basis-[220px] justify-between items-center gap-y-[7px] gap-x-[7px] shadow-[rgba(0,0,0,0.06)_0px_1px_2px_0px] caret-gray-800 [color-scheme:light] select-none px-[7px] rounded-br-[7px] rounded-t-[7px] rounded-bl-[7px] border-[rgba(0,0,0,0.1)] border hover:bg-[rgba(0,0,0,0.05)] ${
                      active ? 'bg-[rgba(255,255,255,0.9)]' : 'bg-[rgba(255,255,255,0.66)]'
                    }`}
                  >
                    <div className="min-w-0 flex overflow-x-hidden overflow-y-hidden grow basis-[0%] items-center gap-y-2 gap-x-2 caret-gray-800 [color-scheme:light] select-none">
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        width="14"
                        height="14"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2px"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        className="align-middle w-3.5 h-3.5 block overflow-x-hidden overflow-y-hidden shrink-0 fill-none stroke-gray-800 stroke-[2px] [stroke-linecap:round] [stroke-linejoin:round] caret-gray-800 [color-scheme:light] select-none"
                        aria-hidden="true"
                      >
                        <path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"></path>
                        <path d="M14 2v4a2 2 0 0 0 2 2h4"></path>
                      </svg>
                      <span className="text-ellipsis [white-space-collapse:collapse] [text-wrap-mode:nowrap] block overflow-x-hidden overflow-y-hidden caret-gray-800 [color-scheme:light] select-none">
                        {tab.label}
                      </span>
                    </div>
                    <span
                      aria-hidden="true"
                      className="bg-[rgba(0,0,0,0)] w-[22px] h-[22px] flex shrink-0 justify-center items-center opacity-50 caret-gray-800 [color-scheme:light] select-none rounded-br-[6px] rounded-t-[6px] rounded-bl-[6px]"
                    >
                      ×
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
        <button
          type="button"
          title="搜索（⌘K）"
          className="bg-[rgba(255,255,255,0.7)] text-gray-800 leading-[20px] text-[14px] flex items-center gap-y-2 gap-x-2 shadow-[rgba(0,0,0,0)_0px_0px_0px_0px,rgba(0,0,0,0)_0px_0px_0px_0px,rgba(0,0,0,0.04)_0px_1px_2px_0px] caret-gray-800 [color-scheme:light] [appearance:button] px-3 py-1.5 rounded-br-full rounded-t-full rounded-bl-full border-[rgba(0,0,0,0.1)] border group"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2px"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="text-center align-middle w-4 h-4 block overflow-x-hidden overflow-y-hidden fill-none stroke-gray-800 stroke-[2px] [stroke-linecap:round] [stroke-linejoin:round] caret-gray-800 [color-scheme:light]"
            aria-hidden="true"
          >
            <circle cx="11" cy="11" r="8"></circle>
            <path d="m21 21-4.3-4.3"></path>
          </svg>
          <span className="text-center text-ellipsis [white-space-collapse:collapse] [text-wrap-mode:nowrap] block overflow-x-hidden overflow-y-hidden caret-gray-800 [color-scheme:light]">
            搜索
          </span>
          <kbd className='bg-[rgba(255,255,255,0.8)] text-[#6f6b66] [font-family:"IBM_Plex_Mono",ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace,"IBM_Plex_Mono",ui-monospace,monospace,system-ui,sans-serif] text-[10px] text-center caret-[#6f6b66] [color-scheme:light] ml-1 px-2 py-0.5 rounded-br-full rounded-t-full rounded-bl-full border-[rgba(0,0,0,0.1)] border'>
            ⌘K
          </kbd>
        </button>
      </div>
    </div>
  );
}

export default Component_2;
