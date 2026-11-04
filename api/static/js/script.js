
document.addEventListener("DOMContentLoaded", function () {

    const nav = document.getElementById("lpNav");
    const toggle = document.getElementById("lpToggle");
    const menu = document.getElementById("lpMenu");

    // Detect landing page using the navbar's data attribute
    const isLandingPage = nav?.dataset.page === "landing";

    // Navbar background
    function handleScroll() {
        if (!nav) return;

        if (isLandingPage) {
            nav.classList.toggle("scrolled", window.scrollY > 30);
        } else {
            nav.classList.add("scrolled");
        }
    }

    if (nav) {
        handleScroll();
        window.addEventListener("scroll", handleScroll, { passive: true });
    }

    // Mobile menu toggle
    if (toggle && menu) {
        toggle.addEventListener("click", function () {
            const isOpen = menu.classList.toggle("active");

            toggle.setAttribute("aria-expanded", isOpen);
            toggle.setAttribute(
                "aria-label",
                isOpen ? "Close menu" : "Open menu"
            );

            const icon = toggle.querySelector("i");
            if (icon) {
                icon.className = isOpen ? "bx bx-x" : "bx bx-menu";
            }
        });

        // Close menu after clicking a link
        menu.querySelectorAll("a").forEach(link => {
            link.addEventListener("click", () => {
                menu.classList.remove("active");
                toggle.setAttribute("aria-expanded", "false");

                const icon = toggle.querySelector("i");
                if (icon) icon.className = "bx bx-menu";
            });
        });
    }

    // User dropdown
    document.addEventListener("click", function (event) {

        const button = event.target.closest("[data-dropdown-button]");
        const currentDropdown = button?.closest("[data-dropdown]");

        document.querySelectorAll("[data-dropdown].active").forEach(dropdown => {
            if (dropdown !== currentDropdown) {
                dropdown.classList.remove("active");
            }
        });

        if (currentDropdown) {
            event.preventDefault();
            currentDropdown.classList.toggle("active");
        }
    });

});


// // const toggle = document.getElementById("menu_toggle");
// // const toggle2 = document.getElementById("menu_toggle2");
// // const menu = document.getElementById("menu");

// // toggle.addEventListener("click", () => {
// //     menu.classList.toggle('active')
// // })
// // toggle2.addEventListener("click", () => {

// //     menu.classList.toggle('active')
// // })

// // document.addEventListener("click", e => {
// //     const isDropdownButton = e.target.closest("[data-dropdown-button]")
// //     if (!isDropdownButton && e.target.closest("[data-dropdown]") != null) return
  
// //     let currentDropdown
// //     if (isDropdownButton) {
// //       currentDropdown = e.target.closest("[data-dropdown]")
// //       currentDropdown.classList.toggle("active")
// //     }
  
// //     document.querySelectorAll("[data-dropdown].active").forEach(dropdown => {
// //       if (dropdown === currentDropdown) return
// //       dropdown.classList.remove("active")
// //     })
// //   })


// // Mobile Navbar Toggle
// const lpToggle = document.getElementById("lpToggle");
// const lpMenu = document.getElementById("lpMenu");

// if (lpToggle && lpMenu) {
//     lpToggle.addEventListener("click", () => {
//         const isOpen = lpMenu.classList.toggle("active");

//         lpToggle.setAttribute("aria-expanded", isOpen);
//         lpToggle.setAttribute(
//             "aria-label",
//             isOpen ? "Close menu" : "Open menu"
//         );

//         lpToggle.querySelector("i").className =
//             isOpen ? "bx bx-x" : "bx bx-menu";
//     });
// }

// // Navbar Scroll Effect
// const lpNav = document.getElementById("lpNav");

// if (lpNav) {
//     const handleScroll = () => {
//         lpNav.classList.toggle("scrolled", window.scrollY > 30);
//     };

//     handleScroll();
//     window.addEventListener("scroll", handleScroll);
// }

// // User Dropdown
// document.querySelectorAll("[data-dropdown-button]").forEach(button => {
//     button.addEventListener("click", event => {
//         event.preventDefault();

//         const dropdown = button.closest("[data-dropdown]");
//         dropdown.classList.toggle("active");
//     });
// });

// // Close dropdown when clicking outside
// document.addEventListener("click", event => {
//     document.querySelectorAll("[data-dropdown].active").forEach(dropdown => {
//         if (!dropdown.contains(event.target)) {
//             dropdown.classList.remove("active");
//         }
//     });
// });

//     document.addEventListener('DOMContentLoaded', function () {
//         var nav = document.getElementById('lpNav');
//         var toggle = document.getElementById('lpToggle');
//         var menu = document.getElementById('lpMenu');

//         function onScroll() {
//             nav.classList.toggle('scrolled', window.scrollY > 20);
//         }
//         window.addEventListener('scroll', onScroll, { passive: true });
//         onScroll();

//         function setMenu(open) {
//             nav.classList.toggle('open', open);
//             toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
//             toggle.querySelector('i').className = open ? 'bx bx-x' : 'bx bx-menu';
//         }
//         toggle.addEventListener('click', function () {
//             setMenu(!nav.classList.contains('open'));
//         });
//         menu.querySelectorAll('a').forEach(function (a) {
//             a.addEventListener('click', function () { setMenu(false); });
//         });

        
//     });