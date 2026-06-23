let prevScrollPos = window.pageYOffset;

window.onscroll = function() {
    const currentScrollPos = window.pageYOffset;

    if (prevScrollPos > currentScrollPos) {
        // Scrolling up
        document.getElementById("navbar").style.top = "0";
    } else {
        // Scrolling down
        document.getElementById("navbar").style.top = "-100px"; // Hide the navbar
    }

    prevScrollPos = currentScrollPos;
}