;; -*- mode: emacs-lisp -*-
;; fsc.el: Autogenerated on Wed Sep 30 16:37:10 2009
(scala-fsc :classes "bin" :classpath
           '("lib/*.jar")
           :source "src")


(scala-fsc-bind-finder [(control ?\,)]
  :exclude (:path "scoring"))
