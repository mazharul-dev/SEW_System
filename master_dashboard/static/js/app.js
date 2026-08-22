const accessRoot = document.querySelector(".page-shell");
const accessApproved = accessRoot?.dataset.accessApproved === "true";
const accessStatus = accessRoot?.dataset.accessStatus || "none";

if (window.lucide && typeof window.lucide.createIcons === "function") {
  window.lucide.createIcons();
}

document.querySelectorAll(".file-drop input[type='file']").forEach((input) => {
  input.addEventListener("change", () => {
    const fileName = input.files && input.files[0] ? input.files[0].name : "";
    const target = input.closest(".file-drop")?.querySelector("small");
    if (target && fileName) {
      target.textContent = fileName;
    }
  });
});

setupJoinFlow();
setupEvasiveCards();
if (!accessApproved) {
  syncAccessState();
  window.__joinStatusPoller = window.setInterval(syncAccessState, 5000);
}

function setupJoinFlow() {
  const joinButtons = Array.from(document.querySelectorAll("[data-open-join]"));
  const joinModal = document.querySelector("[data-join-modal]");
  const messageModal = document.querySelector("[data-message-modal]");
  const joinForm = document.querySelector("[data-join-form]");
  const joinMessage = document.querySelector("[data-join-message]");
  const joinStatusLabel = document.querySelector(".join-button span");
  const joinClose = document.querySelector("[data-close-join]");
  const messageClose = document.querySelector("[data-close-message]");
  const modalInput = joinForm?.querySelector("input[name='email']");

  if (!joinModal || !messageModal || !joinForm) {
    return;
  }

  const openJoin = () => {
    if (isApproved()) {
      showMessage("You are already approved.");
      return;
    }
    joinModal.hidden = false;
    window.requestAnimationFrame(() => {
      modalInput?.focus();
    });
  };

  const closeJoin = () => {
    joinModal.hidden = true;
  };

  const openMessage = (text) => {
    if (joinMessage) {
      joinMessage.textContent = text;
    }
    messageModal.hidden = false;
  };

  const closeMessage = () => {
    messageModal.hidden = true;
  };

  const setJoinButton = (state) => {
    const label = state.approved ? "Approved" : state.status === "pending" ? "Pending" : "Join Now";
    if (joinStatusLabel) {
      joinStatusLabel.textContent = label;
    }
    joinButtons.forEach((button) => {
      button.dataset.joinLabel = label;
      button.classList.toggle("is-approved", state.approved);
      button.classList.toggle("is-pending", !state.approved && state.status === "pending");
      button.setAttribute("aria-disabled", state.approved ? "true" : "false");
    });
  };

  const applyAccess = (state) => {
    accessRoot?.setAttribute("data-access-approved", state.approved ? "true" : "false");
    accessRoot?.setAttribute("data-access-status", state.status || "none");
    accessRoot?.setAttribute("data-access-email", state.email || "");
    setJoinButton(state);
    if (state.approved) {
      unlockCards();
      stopPolling();
    }
  };

  joinButtons.forEach((button) => {
    button.addEventListener("click", () => {
      if (isApproved()) {
        openMessage("Your account is already approved.");
        return;
      }
      openJoin();
    });
  });

  joinClose?.addEventListener("click", closeJoin);
  messageClose?.addEventListener("click", closeMessage);

  [joinModal, messageModal].forEach((modal) => {
    modal.addEventListener("click", (event) => {
      if (event.target === modal) {
        modal.hidden = true;
      }
    });
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      joinModal.hidden = true;
      messageModal.hidden = true;
    }
  });

  joinForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const submitButton = joinForm.querySelector("button[type='submit']");
    const previousLabel = submitButton?.textContent || "Submit";
    const payload = new FormData(joinForm);

    if (submitButton) {
      submitButton.disabled = true;
      submitButton.textContent = "Submitting...";
    }

    try {
      const response = await fetch(joinForm.action, {
        method: "POST",
        body: payload,
        headers: {
          Accept: "application/json",
        },
      });
      const data = await readResponseData(response);
      if (!response.ok) {
        throw new Error(data.detail || data.text || "Join request failed.");
      }

      const state = data.access || { approved: false, status: "pending", email: payload.get("email") || "" };
      applyAccess(state);
      joinForm.reset();
      closeJoin();
      openMessage(data.detail || "01706452007 এই নাম্বারে যোগাযোগ করে approval নিন।");
    } catch (error) {
      openMessage(error instanceof Error ? error.message : "Join request failed.");
    } finally {
      if (submitButton) {
        submitButton.disabled = false;
        submitButton.textContent = previousLabel;
      }
    }
  });

  setJoinButton({
    approved: accessApproved,
    status: accessStatus,
    email: accessRoot?.dataset.accessEmail || "",
  });

  function isApproved() {
    return accessRoot?.dataset.accessApproved === "true";
  }

  function showMessage(text) {
    openMessage(text);
  }

  function unlockCards() {
    document.querySelectorAll(".tool-grid .tool-card[data-tool-card]").forEach((card) => {
      card.classList.remove("is-evading");
      card.style.transform = "";
      card.style.removeProperty("transform");
    });
  }

  function stopPolling() {
    if (window.__joinStatusPoller) {
      window.clearInterval(window.__joinStatusPoller);
      window.__joinStatusPoller = null;
    }
  }

  window.__applyJoinAccessState = applyAccess;
}

function setupEvasiveCards() {
  const grid = document.querySelector(".tool-grid");
  if (!grid) {
    return;
  }

  const cardSelector = ".tool-card[data-tool-card]";
  const cards = Array.from(grid.querySelectorAll(cardSelector));
  if (!cards.length) {
    return;
  }

  const isLocked = () => accessRoot?.dataset.accessApproved !== "true";
  const engage = (card, event) => {
    if (!isLocked()) {
      return;
    }
    const rect = card.getBoundingClientRect();
    const pointerX = event.clientX || rect.left + rect.width / 2;
    const pointerY = event.clientY || rect.top + rect.height / 2;
    const centerX = rect.left + rect.width / 2;
    const centerY = rect.top + rect.height / 2;
    const deltaX = centerX - pointerX;
    const deltaY = centerY - pointerY;
    const distance = Math.hypot(deltaX, deltaY) || 1;
    const magnitude = Math.min(120, Math.max(68, distance * 0.45));
    const tx = clamp((deltaX / distance) * magnitude, -120, 120);
    const ty = clamp((deltaY / distance) * magnitude, -82, 82);
    const tilt = clamp((deltaX / distance) * 5, -7, 7);
    card.classList.add("is-evading");
    card.style.transform = `translate(${tx}px, ${ty}px) rotate(${tilt}deg)`;
  };

  const reset = (card) => {
    card.classList.remove("is-evading");
    card.style.transform = "";
  };

  cards.forEach((card) => {
    card.addEventListener("pointerenter", (event) => engage(card, event));
    card.addEventListener("pointermove", (event) => engage(card, event));
    card.addEventListener("pointerleave", () => reset(card));
    card.addEventListener("click", (event) => {
      if (isLocked()) {
        event.preventDefault();
        const joinButton = document.querySelector("[data-open-join]");
        if (joinButton instanceof HTMLElement) {
          joinButton.click();
        }
      }
    });
  });

  window.addEventListener("resize", () => {
    if (!isLocked()) {
      return;
    }
    cards.forEach((card) => reset(card));
  });
}

async function syncAccessState() {
  if (!accessRoot || accessRoot.dataset.accessApproved === "true") {
    return;
  }

  try {
    const response = await fetch("/join/status", {
      headers: {
        Accept: "application/json",
      },
    });
    if (!response.ok) {
      return;
    }
    const state = await readResponseData(response);
    if (state && state.approved && typeof window.__applyJoinAccessState === "function") {
      window.__applyJoinAccessState(state);
      const messageModal = document.querySelector("[data-message-modal]");
      const messageText = document.querySelector("[data-join-message]");
      if (messageModal && messageText) {
        messageText.textContent = "Your request has been approved.";
        messageModal.hidden = false;
      }
    } else if (state && typeof window.__applyJoinAccessState === "function") {
      window.__applyJoinAccessState(state);
    }
  } catch (error) {
    void error;
  }
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

async function readResponseData(response) {
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return response.json();
  }

  const text = await response.text();
  try {
    return JSON.parse(text);
  } catch (error) {
    void error;
    return { text };
  }
}
