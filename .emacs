;; .emacs

(custom-set-variables
 ;; custom-set-variables was added by Custom.
 ;; If you edit it by hand, you could mess it up, so be careful.
 ;; Your init file should contain only one such instance.
 ;; If there is more than one, they won't work right.
 '(column-number-mode t)
 '(custom-theme-load-path (quote (custom-theme-directory t "/home/mattday/.emacs.d/emacs-color-theme-solarized-master")))
 '(diff-switches "-u")
 '(indent-tabs-mode nil)
 '(tab-width 3))

;;; uncomment for CJK utf-8 support for non-Asian users
;; (require 'un-define)
(custom-set-faces
 ;; custom-set-faces was added by Custom.
 ;; If you edit it by hand, you could mess it up, so be careful.
 ;; Your init file should contain only one such instance.
 ;; If there is more than one, they won't work right.
 )

(load-theme 'solarized t)
(set-frame-font "Hack 12" nil t)
(menu-bar-mode -1)
(tool-bar-mode -1)
(setq inhibit-startup-message t)
(setq initial-scratch-message nil)
(setq split-width-threshold 1 )
(global-set-key (kbd "M-g") `goto-line)
(setq indent-line-function `insert-tab)
