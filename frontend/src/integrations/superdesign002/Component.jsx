import React, { useEffect } from 'react';
import Component_1 from './components/Component_1';
import Component_2 from './components/Component_2';
import Component_3 from './components/Component_3';
import Component_4 from './components/Component_4';
import Component_5 from './components/Component_5';
import Component_6 from './components/Component_6';
import Component_7 from './components/Component_7';
import Component_8 from './components/Component_8';

function App() {
  useEffect(() => {
    // Execute delayed scripts after React has rendered
    console.log('[React] DOM rendered, executing delayed scripts...');

    // Execute regular delayed scripts first
    const delayedScripts = document.querySelectorAll(
      'script[type="text/delayed"]'
    );

    delayedScripts.forEach((script) => {
      const newScript = document.createElement('script');

      // External script (has data-src)
      if (script.dataset.src) {
        newScript.src = script.dataset.src;

        // Copy other attributes (integrity, crossorigin, defer, etc.)
        Array.from(script.attributes).forEach((attr) => {
          if (attr.name !== 'type' && attr.name !== 'data-src') {
            newScript.setAttribute(attr.name, attr.value);
          }
        });
      } else {
        // Inline script
        newScript.textContent = script.textContent;

        // Copy data-* attributes
        Array.from(script.attributes).forEach((attr) => {
          if (attr.name !== 'type' && attr.name.startsWith('data-')) {
            newScript.setAttribute(attr.name, attr.value);
          }
        });
      }

      document.body.appendChild(newScript);
    });

    // Execute delayed module scripts (Pattern 006: Pre-bundled ES Module Scripts)
    const delayedModules = document.querySelectorAll(
      'script[type="text/delayed-module"]'
    );

    delayedModules.forEach((script) => {
      const newScript = document.createElement('script');
      newScript.type = 'module'; // Restore original type

      // External module script (has data-src)
      if (script.dataset.src) {
        newScript.src = script.dataset.src;

        // Copy other attributes (crossorigin, etc.)
        Array.from(script.attributes).forEach((attr) => {
          if (attr.name !== 'type' && attr.name !== 'data-src') {
            newScript.setAttribute(attr.name, attr.value);
          }
        });
      } else {
        // Inline module script
        newScript.textContent = script.textContent;

        // Copy data-* attributes
        Array.from(script.attributes).forEach((attr) => {
          if (attr.name !== 'type' && attr.name.startsWith('data-')) {
            newScript.setAttribute(attr.name, attr.value);
          }
        });
      }

      document.body.appendChild(newScript);
    });

    console.log(
      `[React] Executed ${delayedScripts.length} delayed scripts + ${delayedModules.length} delayed modules`
    );
  }, []);

  return (
    <>
      <div className='bg-[#f7f3ee] text-zinc-950 leading-normal [font-family:DS-SourceSans3,DS-Inter,Inter,-apple-system,"system-ui","Segoe_UI",sans-serif,system-ui,sans-serif] h-full relative isolate caret-zinc-950 [color-scheme:light]'>
        <div id="superdesign-root-002" className="h-full caret-zinc-950 [color-scheme:light]">
          <div
            id="workspace-root"
            className="[--workspace-left-width:280px] [--ws-scrollbar-fade-ms:410ms] bg-[#aba9a5] h-[838px] min-h-[838px] relative flex overflow-x-hidden overflow-y-hidden flex-col gap-y-2 gap-x-2 isolate caret-zinc-950 [color-scheme:light] p-2"
          >
            <div
              aria-hidden="true"
              className="absolute -z-10 caret-zinc-950 [color-scheme:light] pointer-events-none inset-0"
            >
              <div
                className="w-[560px] h-[560px] absolute top-[-160px] left-[-160px] blur-3xl caret-zinc-950 [color-scheme:light] pointer-events-none rounded-br-full rounded-t-full rounded-bl-full right-auto bottom-auto"
                data-style-id="style-0-1775848859187"
              ></div>
              <div
                className="[animation-delay:1.5s] w-[640px] h-[640px] absolute right-[-208px] blur-3xl caret-zinc-950 [color-scheme:light] pointer-events-none rounded-br-full rounded-t-full rounded-bl-full left-auto top-10 bottom-auto"
                data-style-id="style-1-1775848859187"
              ></div>
              <div
                aria-hidden="true"
                className="absolute [background-position-x:2px] [background-position-y:6px] bg-[260px_260px] opacity-[0.04] caret-zinc-950 [color-scheme:light] pointer-events-none inset-0"
                data-style-id="style-2-1775848859187"
              ></div>
            </div>
            <div className="h-11 relative z-[60] shrink-0 caret-zinc-950 [color-scheme:light]">
              <nav className="bg-[rgba(255,255,255,0.72)] w-full h-11 border-t-zinc-200 border-r-zinc-200 border-l-zinc-200 z-50 flex shrink-0 items-center gap-y-3.5 gap-x-3.5 shadow-[rgba(0,0,0,0.06)_0px_1px_2px_0px] backdrop-blur-md [clip-path:inset(0px_round_10px)] caret-zinc-950 [color-scheme:light] px-3.5 rounded-br-[10px] rounded-t-[10px] rounded-bl-[10px] border-b-[rgba(0,0,0,0.05)] border-b">
                <Component_1 />
                <Component_2 />
                <Component_3 />
              </nav>
            </div>
            <div className="w-full min-h-0 relative flex grow basis-[0%] gap-y-0 gap-x-0 caret-zinc-950 [color-scheme:light]">
              <div className="bg-[rgba(34,37,41,0.94)] text-[rgba(242,238,232,0.72)] text-[13px] w-[280px] h-full min-w-[280px] min-h-0 relative z-[5] flex overflow-x-hidden overflow-y-hidden flex-col shadow-[rgba(0,0,0,0.06)_0px_1px_2px_0px] caret-[rgba(242,238,232,0.72)] [color-scheme:light] rounded-br-[10px] rounded-t-[10px] rounded-bl-[10px]">
                <Component_4 />
                <Component_5 />
                <Component_6 />
              </div>
              <div className="mr-[-4px] ml-[-4px] w-2 z-50 flex justify-center items-center opacity-0 caret-zinc-950 [color-scheme:light] hover:opacity-100"></div>
              <div className="min-w-0 min-h-0 relative grow basis-[0%] caret-zinc-950 [color-scheme:light] ml-2">
                <Component_7 />
                <Component_8 />
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

export default App;
