document.addEventListener('DOMContentLoaded', function () {
  // Scroll reveal
  const animateOnScroll = document.querySelectorAll('.animate-on-scroll');

  const reveal = (el) => el.classList.add('show');

  if ('IntersectionObserver' in window) {
    const io = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          reveal(entry.target);
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.15 });

    animateOnScroll.forEach((el) => io.observe(el));
  } else {
    // Fallback
    const checkScroll = function () {
      animateOnScroll.forEach((el) => {
        const rect = el.getBoundingClientRect();
        const windowHeight = window.innerHeight || document.documentElement.clientHeight;
        if (rect.top <= windowHeight * 0.85 && rect.bottom >= 0) {
          reveal(el);
        }
      });
    };
    window.addEventListener('scroll', checkScroll, { passive: true });
    checkScroll();
  }

  // Navbar hover micro-interaction
  const navItems = document.querySelectorAll('.nav-item');
  navItems.forEach((item) => {
    item.addEventListener('mouseenter', function () {
      this.style.transform = 'translateY(-2px)';
    });
    item.addEventListener('mouseleave', function () {
      this.style.transform = 'translateY(0)';
    });
  });
});
