function IconButton({ title, onClick, children }) {
  return (
    <button
      type="button"
      title={title}
      onClick={onClick}
      className="bg-[rgba(0,0,0,0)] text-[#6f6b66] text-[16px] w-8 h-8 relative flex justify-center items-center caret-[#6f6b66] [color-scheme:light] [appearance:button] p-0 rounded-br-[8px] rounded-t-[8px] rounded-bl-[8px] hover:bg-[rgba(0,0,0,0.05)]"
    >
      {children}
    </button>
  );
}

function Component_3({ onOpenReports, onOpenEvidence, onOpenDocs, onOpenTasks }) {
  return (
    <div
      className="flex gap-y-1.5 gap-x-1.5 caret-zinc-950 [color-scheme:light]"
      data-component-id="Component_3"
    >
      <IconButton title="报告中心" onClick={onOpenReports}>
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
          aria-hidden="true"
          className="text-center align-middle w-4 h-4 block overflow-x-hidden overflow-y-hidden fill-none stroke-[#6f6b66] stroke-[2px]"
        >
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"></path>
          <path d="M14 2v6h6"></path>
          <path d="M9 13h6"></path>
          <path d="M9 17h6"></path>
        </svg>
      </IconButton>

      <IconButton title="证据中心" onClick={onOpenEvidence}>
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
          aria-hidden="true"
          className="text-center align-middle w-4 h-4 block overflow-x-hidden overflow-y-hidden fill-none stroke-[#6f6b66] stroke-[2px]"
        >
          <path d="M3 7h18"></path>
          <path d="M3 12h18"></path>
          <path d="M3 17h18"></path>
        </svg>
      </IconButton>

      <IconButton title="文档" onClick={onOpenDocs}>
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
          aria-hidden="true"
          className="text-center align-middle w-4 h-4 block overflow-x-hidden overflow-y-hidden fill-none stroke-[#6f6b66] stroke-[2px]"
        >
          <path d="M12 20h9"></path>
          <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"></path>
        </svg>
      </IconButton>

      <button
        type="button"
        onClick={onOpenTasks}
        className="bg-[rgba(47,52,55,0.1)] text-[#2f3437] text-[12px] font-semibold h-8 flex justify-center items-center shadow-[rgba(47,52,55,0.22)_0px_0px_0px_1px_inset,rgba(0,0,0,0.06)_0px_1px_2px_0px] caret-[#2f3437] [color-scheme:light] [appearance:button] px-3 rounded-br-[8px] rounded-t-[8px] rounded-bl-[8px] hover:bg-[rgba(0,0,0,0.05)]"
      >
        任务空间
      </button>
    </div>
  );
}

export default Component_3;
