




(() => {
    const FI = (window.GravewrightChatInternals = window.GravewrightChatInternals || {});
    const escapeHtml = FI.escapeHtml;

    const COMMAND_DEFS = [
        { token: "/roll", insert: "/roll ", descAttr: "chatCmdRoll" },
        { token: "/gmroll", insert: "/gmroll ", descAttr: "chatCmdGmroll" },
        { token: "/w", insert: "/w ", descAttr: "chatCmdWhisper" },
        { token: "/me", insert: "/me ", descAttr: "chatCmdMe" },
        { token: "/gm", insert: "/gm ", descAttr: "chatCmdGm" },
    ];

    let menuInput = null;
    let menuItems = [];
    let menuIndex = 0;

    function commandMenuFor(form) {
        let menu = form.querySelector(".chat-command-menu");
        if (!menu) {
            menu = document.createElement("div");
            menu.className = "chat-command-menu";
            menu.setAttribute("role", "listbox");
            menu.hidden = true;

            const title = document.body.dataset.chatCommandsTitle;
            if (title) {
                const header = document.createElement("div");
                header.className = "chat-command-menu-title";
                header.textContent = title;
                menu.appendChild(header);
            }

            
            menu.addEventListener("mousedown", (e) => {
                const item = e.target.closest("[data-insert]");
                if (!item) return;
                e.preventDefault();
                completeCommand(item.dataset.insert);
            });

            form.appendChild(menu);
        }
        return menu;
    }

    function hideCommandMenu() {
        if (menuInput) {
            const form = menuInput.closest("[data-chat-form]");
            const menu = form && form.querySelector(".chat-command-menu");
            if (menu) menu.hidden = true;
        }
        menuInput = null;
        menuItems = [];
        menuIndex = 0;
    }

    function highlightCommand() {
        menuItems.forEach((el, i) => {
            const selected = i === menuIndex;
            el.classList.toggle("is-selected", selected);
            if (selected) {
                el.setAttribute("aria-selected", "true");
            } else {
                el.removeAttribute("aria-selected");
            }
        });
    }

    function renderCommandMenu(input) {
        const value = input.value;
        
        if (!/^\/\S*$/.test(value)) {
            hideCommandMenu();
            return;
        }

        const token = value.toLowerCase();
        const matches = COMMAND_DEFS.filter((c) => token === "/" || c.token.startsWith(token));
        if (!matches.length) {
            hideCommandMenu();
            return;
        }

        const form = input.closest("[data-chat-form]");
        if (!form) return;
        const menu = commandMenuFor(form);

        menu.querySelectorAll("[data-insert]").forEach((el) => el.remove());

        menuItems = matches.map((c) => {
            const item = document.createElement("button");
            item.type = "button";
            item.className = "chat-command-item";
            item.setAttribute("role", "option");
            item.dataset.insert = c.insert;
            const desc = document.body.dataset[c.descAttr] || "";
            item.innerHTML = `<span class="chat-command-token">${escapeHtml(c.token)}</span><span class="chat-command-desc">${escapeHtml(desc)}</span>`;
            menu.appendChild(item);
            return item;
        });

        menuInput = input;
        menuIndex = 0;
        highlightCommand();
        menu.hidden = false;
    }

    function completeCommand(insert) {
        if (!menuInput) return;
        const input = menuInput;
        input.value = insert;
        hideCommandMenu();
        input.focus();
        input.setSelectionRange(input.value.length, input.value.length);
    }

    document.addEventListener("input", (e) => {
        const input = e.target.closest("[data-chat-form] textarea[name='message']");
        if (!input) return;
        renderCommandMenu(input);
    });

    
    document.addEventListener(
        "keydown",
        (e) => {
            if (!menuInput || e.target !== menuInput || !menuItems.length) return;

            if (e.key === "ArrowDown") {
                e.preventDefault();
                e.stopPropagation();
                menuIndex = (menuIndex + 1) % menuItems.length;
                highlightCommand();
            } else if (e.key === "ArrowUp") {
                e.preventDefault();
                e.stopPropagation();
                menuIndex = (menuIndex - 1 + menuItems.length) % menuItems.length;
                highlightCommand();
            } else if (e.key === "Enter" || e.key === "Tab") {
                e.preventDefault();
                e.stopPropagation();
                completeCommand(menuItems[menuIndex].dataset.insert);
            } else if (e.key === "Escape") {
                e.preventDefault();
                e.stopPropagation();
                hideCommandMenu();
            }
        },
        true,
    );

    document.addEventListener("focusout", (e) => {
        const input = e.target.closest("[data-chat-form] textarea[name='message']");
        if (input && input === menuInput) {
            
            window.setTimeout(hideCommandMenu, 120);
        }
    });
})();
