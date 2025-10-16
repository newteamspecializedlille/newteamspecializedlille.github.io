// Submenu toggle functionality
document.addEventListener('DOMContentLoaded', function() {
    const submenuToggles = document.querySelectorAll('.hamenu .submenu-toggle');

    submenuToggles.forEach(function(toggle) {
        toggle.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const parentLi = this.closest('.has-submenu');

            // Close other open submenus
            document.querySelectorAll('.hamenu .has-submenu').forEach(function(item) {
                if (item !== parentLi) {
                    item.classList.remove('active');
                }
            });

            // Toggle current submenu
            parentLi.classList.toggle('active');
        });
    });

    // Reset submenu state when menu closes
    const closeMenuBtn = document.querySelector('.hamenu .close-menu');
    const hamenu = document.querySelector('.hamenu');

    if (closeMenuBtn) {
        closeMenuBtn.addEventListener('click', function() {
            // Remove active class from all submenus when closing menu
            document.querySelectorAll('.hamenu .has-submenu').forEach(function(item) {
                item.classList.remove('active');
            });
        });
    }

    // Also reset when clicking outside or on menu-icon to close
    const menuIcon = document.querySelector('.topnav .menu-icon');
    if (menuIcon) {
        menuIcon.addEventListener('click', function() {
            // Check if menu is about to close (is currently open)
            if (hamenu && hamenu.classList.contains('open')) {
                document.querySelectorAll('.hamenu .has-submenu').forEach(function(item) {
                    item.classList.remove('active');
                });
            }
        });
    }
});
