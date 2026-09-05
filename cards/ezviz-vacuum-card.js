/* Carte aspirateur EZVIZ — discrète.

   Une seule ligne, haute comme une tuile : le robot, son état, sa batterie,
   trois commandes. Rien d'autre n'a le droit d'occuper la place en
   permanence. L'entretien attend sous un chevron ; on le consulte une fois
   par mois.

   Le dessin s'efface derrière la photo dès qu'on en fournit une, et le robot
   s'anime quand il travaille — balayage du lidar, anneau qui se propage.
   C'est la seule chose qui bouge.

   Toutes les dimensions dérivent de --fs (font_scale) et --art (size). */

/* Couleur d'état. Discrètes, elles ne servent qu'au point et au balayage. */
const EVC_STATES = {
  cleaning:   {t:'En nettoyage',     col:'#34c759', busy:true},
  returning:  {t:'Retour à la base', col:'#0a84ff', busy:true},
  paused:     {t:'En pause',         col:'#ff9f0a', busy:false},
  docked:     {t:'À la base',        col:'#5ac8fa', busy:false},
  idle:       {t:"À l'arrêt",        col:'#8e8e93', busy:false},
  error:      {t:'Erreur',           col:'#ff453a', busy:false},
  unavailable:{t:'Indisponible',     col:'#8e8e93', busy:false}
};

const EVC_OK   = '#34c759';
const EVC_WARN = '#ff9f0a';
const EVC_LOW  = '#ff453a';

/* Pannes du firmware, traduites. Les absentes s'affichent telles quelles. */
const EVC_FAULTS = {
  CR_RollBrushTwine:'Brosse enroulée', CR_EdgeBrushTrapped:'Brosse latérale coincée',
  CR_WheelTrapped:'Roue bloquée', CR_WheelSuspended:'Roue dans le vide',
  CR_Trapped:'Robot coincé', CR_FailToReturnDock:'Retour impossible',
  CR_LocationFailure:'Perte de repérage', CR_DustBoxOrBagUnset:'Bac absent',
  CR_DustBoxUncover:'Bac ouvert', CR_CleanWaterBoxEmpty:'Réservoir vide',
  CR_CleanWaterBoxLow:'Réservoir bas', CR_CleanWaterBoxUnsetup:'Réservoir absent',
  CR_DirtyWaterBoxFull:'Eau sale pleine', CR_DirtyWaterBoxUnsetup:'Bac eau sale absent',
  CR_AllWaterBoxUnsetup:'Réservoirs absents', CR_MopInstallErr:'Serpillère mal posée',
  CR_MopTryDrop:'Serpillère détachée', CR_RollBrushUnsetup:'Brosse absente',
  CR_LidarCoverErr:'Lidar obstrué', CR_LidarShieldErr:'Lidar masqué',
  CR_DockCommErr:'Base injoignable', CR_DockDryFanStall:'Séchage bloqué',
  CR_DockPumpSewageFail:'Vidange impossible'
};

/* Les deux photos du robot, embarquées dans le fichier.

   Elles ne sont ni configurables, ni téléchargées, ni cherchées dans un
   dossier média : la carte se suffit à elle-même, où qu'elle soit installée
   et quelle que soit la façon dont elle est servie. C'est la seule manière
   d'être sûr que tout le monde les voie sans avoir rien à faire.

   Détourées, recadrées sur le robot puis mises au carré — le balayage du
   lidar est un cercle centré sur le cadre, il n'épouse la coque que si le
   cadre est carré. WebP 224 px : la carte n'affiche que 96 px au maximum,
   224 couvre les écrans à haute densité, et pèse quatre fois moins qu'un
   PNG de même qualité. */
const EVC_PHOTO_DOCKED = 'data:image/webp;base64,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';
const EVC_PHOTO_MOVING = 'data:image/webp;base64,UklGRpgcAABXRUJQVlA4WAoAAAAQAAAA3wAA3wAAQUxQSDcMAAABCUduGzkSHCZX///BM1VdG88R/Z8AdO5Ma9GkCFRrupdsZ5pDQR2wXwH7djTBHi/ABlBtIKJvJ5jPgdX/jeTWFwc3+yV7kyRu9t4Sid2g+5OnVLNrmllXOxtTRj5GgaGgbSOnCX/W9+N+AIiICcgqICetbYBKVoGss57tBU2jpmI3tU8l3RwVD5z2yFH9k30eOwiQZob2OMLeCS1kqtn0MMuCjNXsU0WzyKhtI0Hp7zgcf4QHYABUje4ZMQET4HnbtrVttu3b9lMyyGyHmZNym16Fi5kZZtfNTFO+R/hv8BRnzMzMTIXkKlPAjnUMmjqJI/ucRsQEeNe2bVlr27au56Mk+9H2THeltX9tO9y9uteiUWIkOCFKwT7g47P3blbeGLz5GxETQPz7mUrGc974oeM4jxGve91h5DEwNDcbxupqdJO2oP9RuxRu64+MblWAse12k7UBd43tQd0KoCCdzmTT6WwmymaCgI211XmSptlimW/Qno3bB+a6lShf7h0ZGxjJBw6a8UbonCNu1vMszxez6bDfb9+O45kebCY9jalrkG0S1Eo98ydneyvlfCS2PV3Mptet08PLwSj+P4bug0JjohDTHQoDXP9o/8GTY7VaMaAtk/m4f/SucXM9doCB7hSujA2jLkAyg2hmZPaexZ5ChvbWYnRZ3a93WnMgEvLj3Ph055OIIdo/f+CemUoEGKh9BAako+bL3aP6FCIkn+afqlN0eMmM9N5DB+5bKAYQI0SbC2GGG9e3qzvVGUTSh+I/xqNh7DqYMILBexZPHKwEmCGxSyXMYHb6cudtfUH0If5Z3ztqdGxhRAvP3HZ80IGZxK6WMEOj2vYn3w1AN4nTF+fnUMcyV77jkfwaYCASUGCg7vZX/2jn/0eX/lEZwjpVULv9YTPAcCSmwGB6+NHvG8n/XPxlMORidaRg6P6HrgKYRLIKg6T28Z/3Z9D4x/p4iY4rwci9jyyzqUjovPOH3x/NWDo3O4g6izBqJx5rGolfNP7wu+B6fbCPzipI7318oEHyy3D7bzuUyg9jHUQYC/c+MI6ZEg+EfezdQ+lDFWmGjIHD982GFgd0Rlc9PFQ4OhwrVlh68t4DOUOYqSZq/PoqcWcweu472A+IoXK47OxUGusEqaGDMykQHVZGaXaxQAcs3j1XAdGZx/YOhskmgp6FqRSdWlCZnY9QconM/pkSnT1cWCxiSirC8ZE0Hd6oDvY4EllGpr8Xsw4HZMZHXCLhaqUHENhvqf7hdPKYaXAoHbDY1xsljQjGh9KCREFUTMkSBZX7Q7rKsBCRqGEuS7cZ5lNJEqTToC6D0LmkEEEqpBu1XDoZDAHWjRDafpQAuIodOJWTYwWWqRCbF09NuKIkYE3J7GkZZVJayEA6Xj4pimVO6GaT7AlZcT3HAsdYTlOiQ3BxSQjPhw5RYYwGRRAx7J8KMbzMUAAJ1+yjJ0ByviCUZ90hj16WnV0LBZKbd5amR0be7opgVnRZz3jc4rqfE9JFvSY9KuKDhQVVFFdHPOr5qw6hPdhaPCLRfuMstDg5wtqGUfWW8J4dD2lX13zTIcQHL2Nn7WH1wzTI2NqiPbUa3BLkGr5ZCtpBVu9DCjI7+27D5LRD0qXcMGEu0t+/EsRNC4IHIaY/E2hgN4ovPzqesQ0wuy9xITuIgo3s3S+99QMffGNtmHFvjdU+Z9BuKa6F00dvX1r684//direTNaKuOCqdPHmzn7wM787w0BPdO3sf3/5138tN9lqfWPYmbwh+/7X//z97w4fPDhUrYbXz/3zN/+6dOFG0+dqVKKbl2X4/jVWwNX6JhfGJgfcysrSDz7rsXJ50Jm6OHDF3/8ZITMIqoPTo/37x//+rg/pSi6H6O5T9e/UDZAUG7jM5LS+/qEblwYd3b1IFf/4dzYXUmyAPrRETuruELnGtxqb3Syk2DYTH/8bPlj94bZa8JZlv1j3gtkvfmbaFhj+BX74/U/ZJnf7sieMf862ykqPmSfwt+FY2+BYOIQvdu9kOyx4cMETZOU92VhbUtx7IjI/AG7fx9ZcvNg0XzD2nsC0BTXDow18QRQP57cW9w1j+OPtB9n6ouGTswcwtaSY+VWfsMLhgtG6FYYweYOME3NsdaGEOW8Apsa2NBfjk6K84KwVWThdNnkEcfp4H2qF8pHQKwR7hmnVmDyAX4qBfqy1IeQVWHl/QKuaLMZ4pSyzmEcetcUAeQUw04959MzinwMVWi3WvENUBlrLewfk5lwr1QLyDFlmNt+ChrOGd2o0aiE3nkLeQTXXQjQgwz9LxRYyVXw0H7UQ9XpJtthCpog8JCy0EDp8tKx4rJz1kmbbY+k7mH9o+8xj9Qoe6uK5R1DzETbMQznMP6KNFx5BAQ+1jQ2frI9QiTyUQj6CbwoffWEekpdU5BGveYmZR2MN8w+lziNYQ/7hksJj9VJD5hmyYuw8ml+94B2QNTIPzp3DP4uOfG4sYd6RZviuLOOfSe5lF71DJLHX+invgH7ptdEE8wsxlVc0geQXxg9eeBUGMXxzM8M8wl7kHcUm8lh7Bf+MF5jH9f+A+cb5DN/6/9eFV8rKeoI8WPINSBsZnuLcNcwvbHmF/yv/wy9FPMS8zv0dzCfgcoT/5LgwnpGCUz9Z2U1MzwjMNWMvIrpTnpWW9DPkI3qHzwpxW8fwu96XyR/guHUHbNlKDG+U6fgGecmoXyKPmJ8kxl2P9jFvcPRqmPzExbEz8wU46yLuELn6EF9UlB9eYncAXh8jT4DzrdzcXUT7CMwPjNN9x50VLb6/Ql4gOGnb3YCvj/DF7le56W6yy2rTD4zD77lPRemXp/yA7N11pHsA4tozodFie430s/hZ4PYi07Zg5UeNZ8H71ya2u/Umew7sTtj++G/XKPjiL6MH0F61sMCTNXs8ZO+XQxR2ln628SB6tVUS9LL2IQ/8wO1BV0f9y9FOzb9YMXmLgz/+mZ0Veuik0B4HjS/ldwiYf6JioU1/WGbn9eDtgnRj/atFYTskG7unV5t+ewoZO3/vHYEwZlr5dpY2lFXvekH6l8+heOcQxzcrIWYcOuEQ7RBn3m8GmBi8q2S0p+hpM7wIjh52qD2w+FoBNnd3aLSrXPvqhSmsLLprknbOW2mFoFYwMx+0lU2armLmyeibSFlboc55BWkS0b4abT92PK9gIjM/oPajvz9lgeQqs1NG2wt6BwwLIVUme8vsysyiuSCCT0e0OziQKoTEtJtGu0HQy5yFD4uvJ+xWd367cMGj5dZLdm96dLO00MlOPqWyeyDKB667UVhMmZpQNiULmWy2aUazEbqQcHWpgYyx6wu1QKHiolKaJKwRrK6YIQElZc2FiBylkZBOrmLhYWUJLiFE6VxomFSyQuXmS4cFhVOqVQKaDdIiJNzkJmPFMFTmwqGY9xdo1VCMswKFgMhvBgWrOF1OHQFoSmcxaBWRnlxlsvUmSBeDBSvamPX60xKtM7Q872asbuN6lBTYWSWKtH9wi60uGWm/v8xZ2/lNZ5CbkeyDneaoXEsyl90cnoNY7SK9PDyfl7Z+yMat9gQTK9+4OOjGDq0Xc8nN/qUQa1CQ9XY6U9lacfFp9Zx12to6G5RrRPFgu1aC1oagOH7ZHmldaPB2d4CxXo3B8evDQQFadeLizevtHLF2rdyqp3uKoZMpsWSO2fef/u2DwGCZNS+HlIqhA5REMsr53kefXBIYLWfr51fyvdkwkKGkkZGn1X98WseiswpwtrpydT2dS4WSaZXIyCaHf/yuCxHCdGfXl5cVunRKiUIyOvzNmyuIEGtf1C+eOm0uClbIuLf7+1pNmIkQFDQvnlmO18/er4bkuvfFR41rMBMhub78j1/+7VV75P6ftZuhTfJB6+Sjl+8XBGo0dXx2em64J8vNhtrEAANc3K8efP15A68yyFQPHJpeHC4VnRMYtpkAtaD/ZzcJASziTu3gs1fNDMwLSGZQm58emjgy3JuXEy0aBoYAw/7nlnE2OTs+7x/VroAIkxkQIgZVZqam5ierZ6o9xUwQKx0GgePWTmUJrlG/QeHG8n/qtb1mUoJVDBHAwpkZpMu95fPp3nyhqKBUzecqlUzosMbKbLEYTUR88cpKVF05c3aYgJkJRzgLFxu3loJUEKRyAQ6skeV5XoiCW0cIEd4SmAyM7ZYwk5AIfG2b0SkBAFZQOCA6EAAAsFEAnQEq4ADgAD5hLpNGpCK/oSVVC3PwDAlpbt1gaSg/sb/ePw8/TvzP/0H5LegPmm+Ye2n7cdFdp7nd7QfmDqBeyt6Ztp6BHsl9Y/1/3FfHR9v5xfY//k+4B+qv/G5CX75/rPpA+wX+U/2D/c/438nPlg/2vu992H55/pP+p/ovgH/kH9J/2f9u9tb2c/sV7En6tffsY+z8Zh1UH2+ke15fbL72yzovT6ZDNp4Y097a61HKaz9MDA4wOXVxw9D797MOynMaCq1Hi82H2OH9rrLTMpwrCV+AYE09+bJjmm/NWlK74y9uNaCfpP62lg9tGYt4qdAHFe9u4l/0BxOIVrSzVmTwTjAQJnd+KPguf+JUbCkKYEsPM8Bv2y7AE0hhHSEXsdiZeyGOx1bT89H8fvkBW2aX0vNGuLsWwou++vCj90aoG358RPUz4YJv8a0JeS1fYZTdqKlQ/dmF1Ja6SafQdMcYORLoQE5whUV9D30d0D7jREF3edt+qU7pnJLSHQ2SvaFeGIorSZhfx1zUuhM/+9R9XXDBddYQeI2a36S7EzqWTLhjluNJVL1VmR488Q9RbivcuEM6bsfPu3jods/AH/OcsKKwZkOILOdiEZ8U3oPYugZUUutkS8aNIdJMMaciIe9yYxRa6InOvD1WC6Lx/t6fNuQi6/VJzh7yNC+EA96UCFHreft3YsP7n9003lM+B6ExMCs/jrbucOV0ajl4rEuxzQu+tu1On8oimzN8CjdRhfguZbUwbHUFa01pka9QEJ4vveHW9SzmP6y+3lTqxz3xQUhhrJgbTX6qsVaZRM/K0n4K9RO72uSetxbXPTLnnYEZ9JRUPkStfzsxCtRk2/qg/mW4iu80B/kD5nKLMfOAgAAA/v02e23fJ73j7HbsYSLeN6bNb8thEsJHQrRD9iEtO1l1MiOnhLcYRmGFYUnvyPjSb23hrQaFGYAIwMUWHjd1SoVEf2QTDvnigEre1xwXb96NrR+Z5EusUSPE0tp+bxbUad+3viIpNCQz4EiFSKZREScbQg6ssRhV5pi3mlOAkIN5Oz0DcCn3mvrlLUSDCyFYkeFtZxJGuQKE6PJOIQr+FX8O7N+mNmKb4m3o/dqSNvHGFGLvLtooxbeIeNyjqLZ5e8WRs/2JgUUq7kp5GDKxRp2u5GjKHNxvYNpK+62wH4uIYUGHb1HmyynYogxDPJxkCW/7hgAwXsG40uKd1tSGtP3zhCM5WlLQdl3A+2sGCTu1GKXXMQo19p9WLAZFZvU570kb5593CdFjNnYqeWmmkyFR0EMMFU2as3xs8/1CIjtl6A98bVqUSnWGq4X8T/rR/K0A10SVM754U2tbci76sLpdKAHXHdq4zeCjA0v1Nxapjos2887OnKDqYjL/xs/+mE2XBT2Mh6zouzMi32lUL4WncCdIfjONkjRmkGM1ZHhR3/jHlKqwePLtMlzr61aS28mSV+VYe5ELjPYFXVJ1CRJq+qJFq4JKMgop3NT+JyEw5L2irLdSktxz5vwzLGrqEokCbXHXx/LrP40WHmMtwANETaYrP+cR2hGhIP8tkqH0IqdZdXbh05sOba/BTkPUT1vLfkNJ/icKsuPRz5xp6OxL/wRPKoy51D4pcV62yIQtAmJSTFRiT6/REeDaPDWuiDLnDQpAFhowQ9ve29e/NdFjmTs57qhZH9oAGVHfKZuyozZrZaGbfFRMLF3XTMTkdLZXX2yGjTkD4zX/LlEtDgiWO1wMuwXxFcnJtkuP5QosiNyFv136xmwVKtziuFSf9o+Rk/NGcV8/KZVe90HQFr+YhkFuRvYpGtEBPdhtDo/bCj6w3iXzmWVxYynzIhRqdZ1Oa90F+fy8axj0nDKpF/NgUqlbYaE+aoHCdNAmnDl/EEd/Q6zwwU/B8MlbqAoZt4s6x9M5j0rui1K1bNGYa/zls79mF+fpSgexYQVNBU2Ta+96yFJ0BWCBCMxz1+1EFtg9wEyZJjRRNrAR2MXqu63zVLAGRTu9j/q5Mhvn3xRsXAet7PsNbhHjhtPJXGRJZ6bpuNALWx0+S1jx4G6ZFAYZ4N/Q45qZ5EuyuiXadxnBdpGCmVFpY4tXI/U28fzYiX59oIr6ugwVcbQvwwrFpTp1aH47p+rCiN6dxYKdMN7VM8McfIhsIexNbYyyww6gPQMLG3kj228+ReATlY+mQV/hirSJx0GqhGaYIhsk9YBJRrZqoJUcCUUcmmzIDPkByFdp0Hvpe7aW3Ua3Hzi2PQq0wh1ed770H3qrzZ0L/JQzb8IiqCuboeXGVnVtm5zQerQr0be+2HfebQ/PSApdguxBBiw6CqG4GgoHi+Uzk04+dUSLp7DGmrfCn1nUrX2XL1CPg8MRr+p55MOnainOFeuV3qgK46ZXI47uOwC93UyTDnhJx8/ClxcB2CdTVqmHxwxHrdaqf44zpYHAPNgFPmKsoeW1raGgH+uZ2kN/Bkf+zq5Yt60qnDYbhTb3afhHDmCX0LsZIAJffKvLqPtBzh48esomoeWLgasYyb0IcKWKxqSVnVcMC6Uhe3lavMixBOwFOuQVukTsBRwY9d49jZfI0y7oV+ieZLcfIG66UTtAB1bQ9MJrZDn1ALHuY498w0/PABp4Rq0VE9XyOJAkxgF9yebSbMuBhEJD95+iYkZf+92ABNVFJOBzrl6kP9NblYWRC8AF0sY+dMLtb7d0H07xijr7XVzns4S1yUVUlMyRRI3wk7+OIQkuThgciqxj4YP1wNybEcZkBLc1nhYeoMeSlzo7Dh9+XLBVr/sw6erI7QTFWs0/DGD54eurQ0/YEGuXd0v7u2Dnwpr/wYDxFFIM9XuiNKL2pxk7Vxbjm5uSxmox3NYGCVlm7B8tsW5vt/1+3UbuLlQL5Qyxrwr16+Kz+yN34HMs8THDQQoEMV2pwCyv+bY88I5csarqfuersjM9Fs8dPtLqblP1TAfI5kLxBmCb1IFhhiJgLzqJjhaKAr4PjJVViJiae79wOMIiFjEk+FSZyVG7UDszvZtPrLh7j0DQzo3UjKxcxc0QvlaeUkwGmUzNCO0ZE8lM0U6jEanKcu6Cc51mHAdhilu0WoP6pIV3ruLoFO1k2MZ57gmFAqZIO1zYe0vACwtzCeDsp7/lHgaT8UH9Br3g28y+nXgWQDG9050M+1RSzvCG9v3yjNCg8QYr/oeZyDVha37sgKgKdeFAvjQC16+RhGodvCKlwXOqRXXuNZb8rTvlKDGgw6khZ6u+ALKJASpUk9VEMjVDI0wNe9rWiugqVRUaJgypInQVCAfbDIZuZZGlfe3goFliFdhVQcUSJHS1LXAX9ZlPBlbb2voV8UfYk7Ch3YqmUs6nFYMIUjsCvPXgRWU3muU9YoY+PmpL99Na9o/ZngvkRTbbrvyCczfBOe4RA+4EmbRTP4FichwwoGF9UNUtXFTxjYhniGaJ0C1dWV0U4ERcQFrC6nSGc+TgG9SjuF+PRT9xcf5SgtExa5QhvG3IqexlzqQ6zX+8O6fx4d+/x2C3wnG3tIT/fvc+SKFZ04zUzo4Z8I/EBgLXwX4uDqqZQGj12+hZf7uiMkMD7AmB4oDowA2oKEF/KIWgR24eOAALWLAYKcQvBk64KXfSWm+3ppWMqZSaxj1nItfOGUtLw2b4b9cJ0QPN8JbIAEvcE1EgqefjpfuBeXG2RKO4aPNZK6rXsYuDTtCnHrKoPzvXslvj8P6tz54R4+48s2C1wwEO9BBq/jWR/nJpgxm2YcTjXmJkk6mCCUpdkAMwnK2t4RDaSKBbk22voQ39kR/WBif2UMLF/VH7VsSP3ZlwhHIddFMVruD0pqcQCJT5dpYvRo/FO8SdcXoK+YduUtWHGx9+3FL6cIpsO+TlFUOr5ipMMDZbMJK8MXs7FbG3LgNkfWKhqh9jgUKBnHgbDooKw8gUT+g/L/wjQ1XX0MIOuoXhWbvjMj0H57ZAJFLFvpU0ov83iVZKlw7pRhEzl2AurG/Hauzdm4/fEUlXhdu4inCKmMj3ThCr7Go731KFltnwfLFqI0v9ZtFfX5+cFUksmDXfx6IoW1yY1fSEG1f1e+EThJkWslt/cKrtaoqRaOzDpgJOv9+ikCcSQxZaKLaKA/Zb2vOR3gQ/Yom8qoffiyulmT8ALaZHAfk6mgrhJIGk9XYpqEYBy395YZot7vyWJ1bK++99jEfGlJFjgCtKORP0JJK6XXxE+s1Lkwn6erCHevWTx7LpEL53uivkSo3m2OF9d3P7fWWet+ZZGSWz4f/ZliPxNyM094DoxJGwM43RUnTZww93zocUyubqC6fkRV/5KydfHTJSX4wDYcF/H2aAJMoKEC0a8Kei29yO54BBCWr6t0A9RD4Hv8dkRHof5LGw0pJ54jkc3+o+3oa2xK12xB9iKfPSX2lmjQNnNHgW2xQIoSaPYlS1KWQKgryp+njTjmTXU8BNQwgGUrwYFIwRGkRoBXkJRcDhnhtn57lOHO4QHsC184LkEXj8LT7q//b88Ol4rcM/h5D+Le1GzDCflMOsV5SKuNCwDteg6UUnbLWagI94E1aPc51GffiOb6doE9WlVrr9IW2SHSDl9Sj7K8i+s5zWKfa0yOyaRzdS6TkWTvsAj+C1dAN/8E8T9IM34dTV9D+yuCaWM85CLxnMbCA9vJXiPk8cAUh9VsPJOAkwLeZfSObNwUYj6BOefu1F51uy4Ovekwo9UxUPQtQ8Tjo2G6AlxOHOtabqbWYx6Y1shKTe4zvj7vJpZUzwI4wS4vMzWJHHBthTzDcAAii/Prk1X36pLv6mGSJJgn8wuWrhTboya/qncpKNpDGNsTw4XUE5Khgs3h1KlMDicye2Htrz+Ii1+IWZPrjqCO1P7G9NKXcwyrBQP8pAHJDsx4W8U6b5sK8JW8Lx5s3CT5E1C7WM8v2yf61rIr2XIclAaVidbmuWeWMouEFP/vE+LYtotvBcYyvcb+ICxBh4ul5W1CiV45JLcCBh/IMznt3ZQqa/QStKsyC0NSfT9C70vUvKNF+nApF8edzg7vXkDLPiMHXnTkM/n9je89Aq9WQ42f7nIIhPSKsE0WjXbLbYkutkn3y/bXB7bM57Gony1pqj2m37CIXlmO8Zu+Zjr/YYMSgWsJZMouVpx+S3u5wrqSQSUc3KWIs0uPdU9uvssrIV6vWlr6E7l+cIJS6uOSduLRsLHs/SRK1/8J4IHK7cil2i+a5LcsB3SJ+Si2W9vfZlyQ9Gkrf8cykUzCsffvQho+UU+0q2zUR45IGwSj0U+RohgUimGVN+3dLnfZ9noVLGd2z2jL95j6RLzzaNqTdwWq+eaZ+UFIpsdfbq/8s39Hi4JLu8GhLWCU37zDgCAlr29od5FEV7pCMQsZAHbHlxGX+szLT1HesdBF6gR9PBq5QYTX4P0E12mF58hAN+rBiwLv84HxuvjbYDQ9q/EVZVC+n5XTTJfwt6LiWbxyBEsOCbNpFvGELmbMK5/IIIjqeXW2E6MCFJExnlyoGd/Rn/izT/MkshlO9/HhgdDq8h+F3WYBv+d3WesekiTDmwx3oAAAA=';

function evcNum(v){
  if(v === null || v === undefined) return NaN;
  const t = String(v).trim();
  if(t === '') return NaN;
  const n = Number(t);
  return Number.isFinite(n) ? n : NaN;
}

/* Usure : verte tant qu'il reste de la marge, orange quand il faut y
   penser, rouge quand la pièce est à changer. */
function evcWearColor(w){
  if(isNaN(w)) return '#8e8e93';
  if(w >= 85) return EVC_LOW;
  if(w >= 65) return EVC_WARN;
  return EVC_OK;
}

class EzvizVacuumCard extends HTMLElement{
  constructor(){
    super();
    this.attachShadow({mode:'open'});
    this._built = false;
    this._open = false;
    /* État attendu après un appui, le temps que le robot publie le sien. */
    this._pending = null;
    this._pendUntil = 0;
    /* Manœuvre de dépannage en cours. */
    this._fixing = false;
  }

  setConfig(cfg){
    if(!cfg.entity) throw new Error('Il faut renseigner "entity"');
    if(cfg.entity.split('.')[0] !== 'vacuum')
      throw new Error('Cette carte attend une entité du domaine vacuum');

    this._cfg = Object.assign({
      name:null, battery:null, fault:null,
      consumables:[], consumable_mode:'wear', show_hours:true, alert_wear:85,
      font_scale:1, size:56,
      stuck_after:2, unstick_delay:5
    }, cfg);

    this._cons = (cfg.consumables || []).map(c =>
      typeof c === 'string' ? {entity:c, name:null}
                            : {entity:c.entity, name:c.name || null});
    this._open = !!cfg.expanded;

    this.shadowRoot.innerHTML = `
    <style>
    :host{display:block}

    /* Coins largement arrondis, une bordure à peine visible, une ombre
       douce : la carte se pose sur le fond au lieu de s'y découper. */
    ha-card{
      display:block;position:relative;overflow:hidden;
      container-type:inline-size;
      padding:calc(9px * var(--fs)) calc(13px * var(--fs));
      border-radius:var(--ha-card-border-radius, 22px);
      border:1px solid color-mix(in srgb, var(--primary-text-color) 9%, transparent);
      background:var(--ha-card-background, var(--card-background-color, #fff));
      box-shadow:0 1px 2px rgba(0,0,0,.05), 0 6px 18px rgba(0,0,0,.04);
    }

    .main{display:flex;align-items:center;gap:calc(11px * var(--fs))}

    /* ---- le robot ---- */
    .art{
      flex:none;position:relative;cursor:pointer;
      width:var(--art);height:var(--art);
    }
    .art img{display:block;width:100%;height:100%;object-fit:contain}

    /* Balayage du lidar et anneau qui se propage : les deux seules
       animations de la carte, réservées au travail en cours. */
    .scan{
      position:absolute;inset:0;border-radius:50%;pointer-events:none;
      opacity:0;transition:opacity .5s;
      background:conic-gradient(from 0deg,
        color-mix(in srgb, var(--vc) 55%, transparent) 0deg,
        transparent 55deg, transparent 360deg);
      -webkit-mask:radial-gradient(circle, #000 62%, transparent 63%);
      mask:radial-gradient(circle, #000 62%, transparent 63%);
    }
    .busy .scan{opacity:.9;animation:evc-scan 1.8s linear infinite}
    @keyframes evc-scan{to{transform:rotate(360deg)}}
    .pulse{
      position:absolute;inset:0;border-radius:50%;pointer-events:none;
      border:1.5px solid var(--vc);opacity:0;
    }
    .busy .pulse{animation:evc-ring 1.8s ease-out infinite}
    @keyframes evc-ring{
      0%{opacity:.5;transform:scale(.85)}
      100%{opacity:0;transform:scale(1.14)}
    }

    /* ---- nom, état, batterie ---- */
    .txt{
      flex:1 1 0;min-width:0;cursor:pointer;
      display:flex;flex-direction:column;gap:2px;
    }
    .nm{
      font-size:calc(.66rem * var(--fs));font-weight:600;letter-spacing:.08em;
      text-transform:uppercase;color:var(--secondary-text-color);
      white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
    }
    .st{
      display:flex;align-items:center;gap:calc(6px * var(--fs));
      font-size:calc(.94rem * var(--fs));font-weight:600;
      color:var(--primary-text-color);white-space:nowrap;overflow:hidden;
    }
    /* À l'étroit, c'est le libellé d'état qui cède — jamais la batterie,
       qui est un chiffre : tronquée, elle mentirait. */
    .lbl{flex:0 1 auto;min-width:0;overflow:hidden;text-overflow:ellipsis}
    .dot{
      flex:none;width:calc(7px * var(--fs));height:calc(7px * var(--fs));
      border-radius:50%;background:var(--vc);
    }
    .busy .dot{animation:evc-dot 1.3s ease-in-out infinite}
    @keyframes evc-dot{50%{opacity:.25;transform:scale(.7)}}
    .st.err{color:var(--vc)}
    /* La batterie suit l'état sur la même ligne : deux informations, une
       seule hauteur. */
    .bat{
      flex:none;font-weight:500;color:var(--secondary-text-color);
      font-variant-numeric:tabular-nums;
    }
    .bat.low{color:#ff453a}
    /* L'éclair de charge en icône, pas en emoji : un emoji garde ses propres
       couleurs et jure avec le thème. */
    .chg{
      flex:none;display:none;color:var(--secondary-text-color);
      --mdc-icon-size:calc(14px * var(--fs));
    }
    .chg.on{display:inline-flex}

    /* ---- commandes ----
       Trois pastilles rondes, contour discret, remplies seulement quand la
       commande est celle en cours. */
    .cmd{flex:none;display:flex;gap:calc(6px * var(--fs))}
    .ico{
      width:calc(34px * var(--fs));height:calc(34px * var(--fs));
      flex:none;border:0;padding:0;border-radius:50%;cursor:pointer;
      display:flex;align-items:center;justify-content:center;
      background:color-mix(in srgb, var(--primary-text-color) 6%, transparent);
      color:var(--primary-text-color);
      transition:background .18s, transform .12s, opacity .18s;
      -webkit-tap-highlight-color:transparent;
    }
    .ico ha-icon{--mdc-icon-size:calc(18px * var(--fs));opacity:.75}
    .ico:hover:not(:disabled){
      background:color-mix(in srgb, var(--primary-text-color) 12%, transparent)}
    .ico:active:not(:disabled){transform:scale(.92)}
    /* Une commande indisponible disparaît au lieu de se griser : elle ne dit
       rien d'utile, et sa place rendue au texte évite que l'état soit
       tronqué sur une carte étroite. */
    .ico.gone{display:none}

    /* ---- dépannage ----
       Absent tant que tout va bien. Quand le robot s'immobilise, il apparaît
       en rouge et clignote, comme le triangle de détresse d'une voiture :
       c'est une anomalie, elle a le droit d'attirer l'œil.

       Sa visibilité passe par la classe « show », et surtout pas par « on » :
       cette dernière marque la commande en cours et porte la couleur d'état,
       qui l'emporterait sur le rouge.

       (Pas d'accent grave dans ce commentaire : tout ce bloc CSS vit dans un
       littéral de gabarit, un seul accent grave y fermerait la chaîne.) */
    .fix{display:none;background:color-mix(in srgb, #ff453a 16%, transparent)}
    .fix.show{display:flex;animation:evc-blink 1.1s ease-in-out infinite}
    .fix ha-icon{color:#ff453a;opacity:1}
    .fix:hover:not(:disabled){
      background:color-mix(in srgb, #ff453a 28%, transparent)}
    @keyframes evc-blink{50%{opacity:.35}}

    /* Le chevron n'est pas une commande : plus petit, sans fond. */
    .chev{
      width:calc(22px * var(--fs));height:calc(34px * var(--fs));
      background:transparent;
    }
    .chev ha-icon{--mdc-icon-size:calc(20px * var(--fs));opacity:.45;
      transition:transform .3s ease}
    .chev:hover{background:transparent}
    .chev.open ha-icon{transform:rotate(180deg)}
    /* Une pièce en fin de vie : un point rouge sur le chevron, sans
       clignotement — il attend qu'on ouvre, il n'a pas à s'agiter. */
    .chev.warn::after{
      content:'';position:absolute;margin:-14px 0 0 13px;
      width:6px;height:6px;border-radius:50%;background:#ff453a;
    }

    /* ---- entretien, replié ---- */
    .fold{display:grid;grid-template-rows:0fr;
      transition:grid-template-rows .3s ease}
    .fold.open{grid-template-rows:1fr}
    .foldin{overflow:hidden;min-height:0}
    .cons{
      display:grid;grid-template-columns:1fr 1fr;
      gap:calc(8px * var(--fs)) calc(16px * var(--fs));
      margin-top:calc(9px * var(--fs));padding-top:calc(9px * var(--fs));
      border-top:1px solid
        color-mix(in srgb, var(--primary-text-color) 8%, transparent);
    }
    .c .l{display:flex;align-items:baseline;gap:6px;margin-bottom:3px}
    .c .k{
      flex:1 1 auto;min-width:0;font-size:calc(.74rem * var(--fs));
      color:var(--secondary-text-color);
      white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
    }
    .c .v{flex:none;font-size:calc(.76rem * var(--fs));font-weight:600;
      color:var(--wc);font-variant-numeric:tabular-nums}
    .c .v small{font-weight:500;opacity:.65}
    .bar{height:3px;border-radius:999px;overflow:hidden;
      background:color-mix(in srgb, var(--primary-text-color) 9%, transparent)}
    .bar i{display:block;height:100%;border-radius:999px;
      transition:width .6s ease}

    /* Carte étroite : le nom s'efface avant tout le reste, l'état suffit. */
    @container (max-width: 340px){
      .cons{grid-template-columns:1fr}
      .nm{display:none}
      .main{gap:calc(8px * var(--fs))}
      /* Le robot cède quelques pixels avant que l'état ne soit tronqué. */
      .art{width:calc(var(--art) * .82);height:calc(var(--art) * .82)}
    }
    </style>
    <ha-card>
      <div class="main">
        <div class="art"><img alt="">
          <div class="scan"></div><div class="pulse"></div></div>
        <div class="txt">
          <div class="nm"></div>
          <div class="st">
            <span class="dot"></span><span class="lbl"></span>
            <span class="bat"></span>
            <ha-icon class="chg" icon="mdi:lightning-bolt"></ha-icon>
          </div>
        </div>
        <div class="cmd">
          <button class="ico fix" title="Débloquer : retour à la base, puis relance">
            <ha-icon icon="mdi:hazard-lights"></ha-icon></button>
          <button class="ico go" title="Démarrer">
            <ha-icon icon="mdi:play"></ha-icon></button>
          <button class="ico pause" title="Pause">
            <ha-icon icon="mdi:pause"></ha-icon></button>
          <button class="ico home" title="Retour à la base">
            <ha-icon icon="mdi:home-import-outline"></ha-icon></button>
        </div>
        <button class="ico chev" title="Entretien">
          <ha-icon icon="mdi:chevron-down"></ha-icon></button>
      </div>
      <div class="fold"><div class="foldin"><div class="cons"></div></div></div>
    </ha-card>`;

    const r = this.shadowRoot;
    this._el = {
      card:r.querySelector('ha-card'), main:r.querySelector('.main'),
      art:r.querySelector('.art'), img:r.querySelector('.art img'),
      nm:r.querySelector('.nm'), st:r.querySelector('.st'),
      lbl:r.querySelector('.lbl'), bat:r.querySelector('.bat'),
      chg:r.querySelector('.chg'),
      fix:r.querySelector('.fix'),
      go:r.querySelector('.go'), pause:r.querySelector('.pause'),
      home:r.querySelector('.home'), chev:r.querySelector('.chev'),
      fold:r.querySelector('.fold'), cons:r.querySelector('.cons')
    };
    this._el.card.style.setProperty('--fs', String(this._cfg.font_scale));
    this._el.card.style.setProperty('--art',
      Math.round(this._cfg.size * this._cfg.font_scale) + 'px');

    this._el.fix.addEventListener('click', () => this._unstick());
    this._el.go.addEventListener('click', () => this._call('start'));
    this._el.pause.addEventListener('click', () => this._call('pause'));
    this._el.home.addEventListener('click', () => this._call('return_to_base'));
    this._el.chev.addEventListener('click', () => {
      this._open = !this._open;
      this._el.fold.classList.toggle('open', this._open);
      this._el.chev.classList.toggle('open', this._open);
    });

    const more = () => {
      const ev = new Event('hass-more-info', {bubbles:true, composed:true});
      ev.detail = {entityId:this._cfg.entity};
      this.dispatchEvent(ev);
    };
    this._el.art.addEventListener('click', more);
    this._el.st.addEventListener('click', more);

    this._el.fold.classList.toggle('open', this._open);
    this._el.chev.classList.toggle('open', this._open);
    this._built = true;
  }

  /* Le robot est-il immobilisé ?

     Ni le capteur de panne ni l'état `error` ne servent à rien ici : sur ce
     firmware, `CurrentTask.exception` ne remonte pas les incidents physiques
     — vérifié sur dix jours d'historique, il n'a jamais quitté « ok », y
     compris pendant des blocages avérés. On les surveille quand même, au cas
     où un autre modèle serait plus bavard.

     Le vrai signal, mesuré en direct sur un robot coincé : **il se tait**.
     `task_state` passe à vide et n'en bouge plus. L'état de l'entité, lui,
     reste « en nettoyage » — l'intégration a un garde anti-clignotement qui
     conserve l'activité précédente quand `task_state` se vide, si bien que
     l'entité ne basculera jamais d'elle-même.

     On mesure donc le silence : hors de sa base, `task_state` vide depuis
     assez longtemps. `last_updated` date le dernier changement d'attribut,
     donc l'instant où il s'est tu. Le clignotement connu de `task_state` —
     il alterne toutes les 20 à 40 secondes pendant un nettoyage normal — ne
     peut pas déclencher : chaque alternance remet ce compteur à zéro.

     L'`idle` prolongé reste surveillé : c'est l'autre forme d'immobilité,
     celle où le robot annonce un état au lieu de se taire. */
  _stuck(){
    const c = this._cfg, h = this._hass;
    if(!h || this._pending || this._fixing) return false;
    const st = h.states[c.entity];
    if(!st) return false;

    if(st.state === 'error') return true;
    if(c.fault){
      const fs = h.states[c.fault];
      if(fs && fs.state && !['ok','unknown','unavailable',''].includes(
          String(fs.state).toLowerCase())) return true;
    }

    const seuil = evcNum(c.stuck_after) || 2;
    const a = st.attributes || {};

    /* Un dépannage remet le compteur à zéro. Sans ça, le robot met jusqu'à
       une minute à se remettre à parler — le temps du relevé suivant — et
       l'horodatage d'origine, lui, est toujours vieux de dix minutes : le
       triangle réapparaîtrait aussitôt après avoir été pressé. */
    const depuis = (horodatage) =>
      (Date.now() - Math.max(new Date(horodatage).getTime(),
                             this._fixedAt || 0)) / 60000;

    /* Muet et hors de sa base — le cas des vrais blocages. Ce qui borne ce
       seuil par le bas, c'est le clignotement de `task_state` : il alterne
       toutes les 20 à 40 secondes pendant un nettoyage normal. Deux minutes
       laissent trois fois cette marge ; descendre à une minute ferait
       clignoter le triangle alors que tout va bien. */
    if(!a.in_charging && !a.task_state) return depuis(st.last_updated) >= seuil;

    /* Arrêté et bavard : le robot annonce un état au lieu de se taire.
       Même seuil que le silence — un seul réglage, un seul comportement.

       Ne pas le descendre par réflexe : « à l'arrêt » n'est pas rare et
       n'est presque jamais un blocage. Sur dix jours d'historique, dix-sept
       passages en `idle` se sont résolus seuls, de 23 secondes à 2 min 22,
       la moitié suivis d'un retour en nettoyage. À deux minutes, un seul
       d'entre eux déclencherait encore ; à deux secondes, les dix-sept —
       et chacun invite à appuyer sur un bouton qui relance une session. */
    if(st.state === 'idle') return depuis(st.last_changed) >= seuil;

    return false;
  }

  /* Retour à la base, puis relance.

     Une fois le robot dégagé à la main, la pause ne le repart pas : il faut
     lui redonner un ordre de retour, qui solde la tâche en cours, avant de
     pouvoir en lancer une nouvelle. Le bouton enchaîne les deux, avec le
     délai qu'on laisserait en le faisant soi-même. */
  async _unstick(){
    if(!this._hass || this._fixing) return;
    this._fixing = true;
    /* Le triangle s'efface au clic, pas à la fin de la manœuvre : un bouton
       qui reste allumé cinq secondes après qu'on l'a pressé donne
       l'impression de n'avoir rien fait. */
    this._fixedAt = Date.now();
    this._paint();

    const cible = {entity_id:this._cfg.entity};
    this._hass.callService('vacuum', 'return_to_base', {}, cible);

    const attente = (evcNum(this._cfg.unstick_delay) || 5) * 1000;
    await new Promise(r => setTimeout(r, attente));

    this._hass.callService('vacuum', 'start', {}, cible);
    this._fixing = false;
    /* Le robot met une vingtaine de secondes à publier son nouvel état. */
    this._pending = 'cleaning';
    this._pendUntil = Date.now() + 30000;
    this._paint();
  }

  _call(service){
    if(!this._hass) return;
    /* Le robot met une vingtaine de secondes à publier son nouvel état. On
       affiche donc l'état attendu sans attendre, quitte à le corriger si
       l'appareil dit autre chose. */
    const expect = {start:'cleaning', pause:'paused',
                    return_to_base:'returning'}[service];
    if(expect){
      this._pending = expect;
      this._pendUntil = Date.now() + 30000;
      this._paint();
    }
    this._hass.callService('vacuum', service, {}, {entity_id:this._cfg.entity});
  }

  /* Un robot immobilisé ne publie plus rien : sans état qui change, Home
     Assistant ne réveille jamais la carte, et le bouton de dépannage
     n'apparaîtrait donc jamais. On se redessine donc de nous-mêmes, une fois
     par demi-minute, uniquement pour regarder l'heure. */
  connectedCallback(){
    const rafraichir = () => { if(this._built && this._hass) this._paint(); };
    clearInterval(this._tick);
    this._tick = setInterval(rafraichir, 30000);

    /* La minuterie ne suffit pas : un navigateur ralentit, voire gèle, les
       pages laissées en arrière-plan — c'est la vie d'une tablette murale en
       veille. Elle se réveillerait donc avec un calcul vieux de plusieurs
       minutes. On recalcule dès qu'elle redevient visible. */
    this._reveil = rafraichir;
    document.addEventListener('visibilitychange', this._reveil);
    window.addEventListener('focus', this._reveil);
  }
  disconnectedCallback(){
    clearInterval(this._tick);
    this._tick = null;
    document.removeEventListener('visibilitychange', this._reveil);
    window.removeEventListener('focus', this._reveil);
  }

  set hass(h){
    this._hass = h;
    if(this._pending){
      const st = h.states[this._cfg.entity];
      if((st && st.state === this._pending) || Date.now() > this._pendUntil)
        this._pending = null;
    }
    if(this._built) this._paint();
  }

  _paint(){
    const c = this._cfg, e = this._el;
    const st = this._hass.states[c.entity];
    const state = this._pending || (st ? st.state : 'unavailable');
    const info = EVC_STATES[state] || {t:state, col:'#8e8e93', busy:false};

    e.card.style.setProperty('--vc', info.col);
    e.nm.textContent = c.name || (st ? st.attributes.friendly_name : 'Aspirateur');

    /* Sur sa station quand il y est, vu de dessus dès qu'il en part. */
    const photo = state === 'docked' ? EVC_PHOTO_DOCKED : EVC_PHOTO_MOVING;
    if(e.img.getAttribute('src') !== photo) e.img.setAttribute('src', photo);

    /* Coincé, le robot continue d'annoncer « en nettoyage » : c'est le
       propre de la panne, il ne sait pas qu'il ne va nulle part. La carte,
       elle, ne peut pas afficher le triangle d'alerte à côté d'un point vert
       et d'un balayage qui tourne — elle se contredirait. */
    const coince = this._stuck();

    e.main.classList.toggle('busy', info.busy && !coince);

    /* Une panne nommée prime sur tout : c'est l'information la plus utile. */
    let fault = '';
    if(c.fault){
      const fs = this._hass.states[c.fault];
      if(fs && fs.state && !['ok','unknown','unavailable',''].includes(
          String(fs.state).toLowerCase()))
        fault = EVC_FAULTS[fs.state] || fs.state;
    }
    const alerte = fault || (coince ? 'Bloqué' : '');
    if(alerte) e.card.style.setProperty('--vc', EVC_LOW);
    e.lbl.textContent = alerte || info.t;
    e.st.classList.toggle('err', !!alerte);

    /* ---- batterie, sur la même ligne que l'état ---- */
    let pct = NaN;
    if(c.battery){
      const bs = this._hass.states[c.battery];
      pct = bs ? evcNum(bs.state) : NaN;
    }
    if(isNaN(pct) && st) pct = evcNum(st.attributes.battery_level);
    const charging = !!(st && st.attributes.in_charging) && pct < 100;
    e.bat.textContent = isNaN(pct) ? '' : '· ' + Math.round(pct) + ' %';
    e.bat.classList.toggle('low', !isNaN(pct) && pct <= 20);
    e.chg.classList.toggle('on', charging);

    /* ---- entretien ----
       Le capteur donne les heures restantes, son attribut les heures faites :
       leur somme est la durée de vie totale, d'où l'usure. */
    const wearMode = c.consumable_mode !== 'remaining';
    const alertAt = evcNum(c.alert_wear);
    const seuil = isNaN(alertAt) ? 85 : alertAt;
    const worn = [];
    let rows = '';
    for(const cons of this._cons){
      const cs = this._hass.states[cons.entity];
      const label = cons.name ||
        (cs ? String(cs.attributes.friendly_name || cons.entity)
                .replace(/^RE5 Plus\s+/i, '') : cons.entity);
      let val = '—', pctBar = 0, col = '#8e8e93';
      if(cs && !['unavailable','unknown'].includes(cs.state)){
        const remain = evcNum(cs.state);
        const used = evcNum(cs.attributes.hours_used);
        const total = (!isNaN(remain) && !isNaN(used)) ? remain + used : NaN;
        if(!isNaN(total) && total > 0){
          const wear = Math.round((used / total) * 100);
          const shown = wearMode ? wear : 100 - wear;
          col = evcWearColor(wear);
          if(wear >= seuil) worn.push(label);
          pctBar = shown;
          val = shown + '<small> %</small>' +
            (c.show_hours ? '<small> · ' + Math.round(remain) + ' h</small>' : '');
        }else if(!isNaN(remain)){
          val = Math.round(remain) + '<small> h</small>';
        }
      }
      rows += '<div class="c" style="--wc:' + col + '">' +
        '<div class="l"><span class="k">' + label + '</span>' +
        '<span class="v">' + val + '</span></div>' +
        '<div class="bar"><i style="width:' + pctBar + '%;background:' +
        col + '"></i></div></div>';
    }
    e.cons.innerHTML = rows;
    e.chev.style.display = rows ? '' : 'none';
    e.chev.classList.toggle('warn', worn.length > 0);
    e.chev.title = worn.length ? 'À remplacer : ' + worn.join(', ') : 'Entretien';

    /* ---- dépannage ----
       Le second argument de classList.toggle doit être un vrai booléen : un
       `undefined` n'est pas « faux », il fait basculer la classe au lieu de
       la retirer, et le bouton s'allumerait un redessin sur deux. */
    e.fix.classList.toggle('show', coince);
    e.fix.disabled = !!this._fixing;

    /* ---- commandes ----
       On n'affiche que ce qui est faisable ici et maintenant. En nettoyage,
       « Démarrer » n'a plus de sens et s'efface ; à la base, ce sont « Pause »
       et « Retour à la base » qui disparaissent. La place ainsi rendue revient
       au libellé d'état, qui sinon se retrouve tronqué. */
    const dead = !st || state === 'unavailable';
    const commande = (el, faisable) => {
      el.classList.toggle('gone', !faisable);
      el.disabled = !faisable;
    };
    commande(e.go,    !dead && state !== 'cleaning');
    commande(e.pause, !dead && (state === 'cleaning' || state === 'returning'));
    commande(e.home,  !dead && state !== 'docked' && state !== 'returning');
  }

  getCardSize(){ return 1; }

  static getConfigElement(){
    return document.createElement('ezviz-vacuum-card-editor');
  }
  static getStubConfig(hass){
    const first = hass
      ? Object.keys(hass.states).find(id => id.startsWith('vacuum.'))
      : null;
    return {entity:first || 'vacuum.robot'};
  }
}

/* ---------------------------------------------------------------------
   Éditeur visuel, sur `ha-form` : on hérite des sélecteurs natifs de Home
   Assistant (choix d'entité, curseurs) sans les réécrire.
   --------------------------------------------------------------------- */
const EVC_SCHEMA = [
  {name:'entity', required:true, selector:{entity:{domain:'vacuum'}}},
  {name:'name', selector:{text:{}}},
  {name:'battery',
   selector:{entity:{domain:'sensor', device_class:'battery'}}},
  {name:'fault', selector:{entity:{domain:'sensor'}}},
  {name:'consumables',
   selector:{entity:{domain:'sensor', multiple:true}}},

  /* `name:''` est obligatoire : avec un nom, ha-form range les champs de la
     section dans un sous-objet portant ce nom, et la carte, qui les lit à la
     racine, ne voit plus rien changer. Le titre passe par `title`. */
  {name:'', type:'expandable', title:'Apparence', schema:[
    {name:'size',
     selector:{number:{min:40, max:96, step:2, mode:'slider'}}},
    {name:'font_scale',
     selector:{number:{min:.8, max:1.3, step:.02, mode:'slider'}}}
  ]},

  {name:'', type:'expandable', title:'Dépannage', schema:[
    {name:'stuck_after',
     selector:{number:{min:1, max:30, step:1, mode:'slider'}}},
    {name:'unstick_delay',
     selector:{number:{min:2, max:20, step:1, mode:'slider'}}}
  ]},

  {name:'', type:'expandable', title:'Entretien', schema:[
    {name:'consumable_mode', selector:{select:{mode:'dropdown', options:[
      {value:'wear', label:'Usure (100 % = à remplacer)'},
      {value:'remaining', label:'Restant (0 % = à remplacer)'}
    ]}}},
    {name:'alert_wear',
     selector:{number:{min:50, max:100, step:1, mode:'slider'}}},
    {name:'show_hours', selector:{boolean:{}}},
    {name:'expanded', selector:{boolean:{}}}
  ]}
];

const EVC_LABELS = {
  entity:'Aspirateur', name:'Titre affiché',
  battery:'Capteur de batterie', fault:'Capteur de panne',
  consumables:'Consommables suivis',
  size:'Taille du robot (px)', font_scale:'Taille du texte',
  stuck_after:'Immobile depuis (min)',
  unstick_delay:'Délai avant la relance (s)',
  consumable_mode:'Afficher',
  alert_wear:'Seuil du point d\'alerte (%)',
  show_hours:'Afficher les heures restantes',
  expanded:'Entretien déplié par défaut'
};

const EVC_HELPERS = {
  size:'C\'est elle qui fixe la hauteur de la carte.',
  stuck_after:'Immobilité au-delà de laquelle le triangle apparaît. Sous '
    + '2 minutes, il se déclenchera aussi sur des arrêts parfaitement '
    + 'normaux, qui durent jusqu'à 2 min 22.',
  unstick_delay:'Entre le retour à la base et la relance.',
  alert_wear:'Au-delà, un point rouge apparaît sur le chevron.'
};

class EzvizVacuumCardEditor extends HTMLElement{
  setConfig(config){
    this._config = config || {};
    this._render();
  }
  set hass(h){
    this._hass = h;
    if(this._form) this._form.hass = h;
  }

  _render(){
    if(!this._form){
      const f = document.createElement('ha-form');
      f.computeLabel = sc => EVC_LABELS[sc.name] || sc.name;
      f.computeHelper = sc => EVC_HELPERS[sc.name] || '';
      f.addEventListener('value-changed', ev => {
        ev.stopPropagation();
        this.dispatchEvent(new CustomEvent('config-changed', {
          detail:{config:this._toConfig(ev.detail.value)},
          bubbles:true, composed:true
        }));
      });
      this.appendChild(f);
      this._form = f;
    }
    this._form.schema = EVC_SCHEMA;
    if(this._hass) this._form.hass = this._hass;
    this._form.data = this._toForm(this._config);
  }

  /* Le sélecteur de consommables ne rend que des identifiants ; la carte, elle,
     accepte aussi la forme {entity, name}. */
  _toForm(cfg){
    return Object.assign({}, cfg, {
      consumables:(cfg.consumables || []).map(
        c => typeof c === 'string' ? c : c.entity)
    });
  }

  _toConfig(data){
    const out = Object.assign({type:this._config.type}, data);
    for(const k of Object.keys(out))
      if(out[k] === undefined || out[k] === '') delete out[k];
    return out;
  }
}

if(!customElements.get('ezviz-vacuum-card-editor'))
  customElements.define('ezviz-vacuum-card-editor', EzvizVacuumCardEditor);

if(!customElements.get('ezviz-vacuum-card'))
  customElements.define('ezviz-vacuum-card', EzvizVacuumCard);
/* Alias : les tableaux de bord qui utilisaient déjà ce nom continuent de
   fonctionner sans modification. */
if(!customElements.get('maison-vacuum-card'))
  customElements.define('maison-vacuum-card', class extends EzvizVacuumCard{});

window.customCards = window.customCards || [];
window.customCards.push({
  type:'ezviz-vacuum-card', name:'EZVIZ — Aspirateur',
  description:'Carte compacte : etat, batterie, commandes, entretien repliable',
  preview:true
});
