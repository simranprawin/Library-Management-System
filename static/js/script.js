// ==========================================
// LIBRARY MANAGEMENT SYSTEM
// Main JavaScript
// ==========================================


// Wait until the page is fully loaded
document.addEventListener("DOMContentLoaded", function () {

    // ==========================================
    // AUTO-HIDE FLASH MESSAGES
    // ==========================================

    const flashMessages = document.querySelectorAll(".flash");

    flashMessages.forEach(function (message) {

        setTimeout(function () {

            message.style.opacity = "0";
            message.style.transform = "translateY(-10px)";
            message.style.transition = "0.4s ease";

            setTimeout(function () {
                message.remove();
            }, 400);

        }, 4000);

    });


    // ==========================================
    // CONFIRM DELETE ACTION
    // ==========================================

    const deleteButtons = document.querySelectorAll(
        ".delete-btn"
    );

    deleteButtons.forEach(function (button) {

        button.addEventListener("click", function (event) {

            const confirmed = confirm(
                "Are you sure you want to delete this book?"
            );

            if (!confirmed) {
                event.preventDefault();
            }

        });

    });


    // ==========================================
    // SEARCH INPUT
    // ==========================================

    const searchInput = document.querySelector(
        "#searchInput"
    );

    if (searchInput) {

        searchInput.addEventListener("input", function () {

            const searchValue =
                searchInput.value.toLowerCase().trim();

            const bookCards =
                document.querySelectorAll(".book-card");

            bookCards.forEach(function (card) {

                const text =
                    card.textContent.toLowerCase();

                if (text.includes(searchValue)) {

                    card.style.display = "";

                } else {

                    card.style.display = "none";

                }

            });

        });

    }


    // ==========================================
    // PASSWORD SHOW / HIDE
    // ==========================================

    const passwordToggle =
        document.querySelector("#passwordToggle");

    const passwordInput =
        document.querySelector("#password");

    if (passwordToggle && passwordInput) {

        passwordToggle.addEventListener(
            "click",
            function () {

                if (passwordInput.type === "password") {

                    passwordInput.type = "text";

                    passwordToggle.textContent = "Hide";

                } else {

                    passwordInput.type = "password";

                    passwordToggle.textContent = "Show";

                }

            }
        );

    }


    // ==========================================
    // MOBILE NAVIGATION
    // ==========================================

    const menuButton =
        document.querySelector("#menuButton");

    const navLinks =
        document.querySelector(".nav-links");

    if (menuButton && navLinks) {

        menuButton.addEventListener(
            "click",
            function () {

                navLinks.classList.toggle("show");

            }
        );

    }


    // ==========================================
    // FORM SUBMISSION LOADING STATE
    // ==========================================

    const forms =
        document.querySelectorAll("form");

    forms.forEach(function (form) {

        form.addEventListener(
            "submit",
            function () {

                const submitButton =
                    form.querySelector(
                        'button[type="submit"]'
                    );

                if (submitButton) {

                    submitButton.disabled = true;

                    submitButton.style.opacity = "0.7";

                    submitButton.textContent =
                        "Processing...";

                }

            }
        );

    });


    // ==========================================
    // CURRENT YEAR
    // ==========================================

    const yearElement =
        document.querySelector("#currentYear");

    if (yearElement) {

        yearElement.textContent =
            new Date().getFullYear();

    }

});