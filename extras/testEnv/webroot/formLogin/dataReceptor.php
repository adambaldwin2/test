<?

if ( strcmp( $_COOKIE["magicValue"] , '0000-1111-2222-3333-4444') == 0 ){
  echo '<a href="onlyUsers.php">onlyUsers.php</a>';
}
  

if ( strcmp($_POST['user'],"salvatore.vassallo") == 0 && strcmp($_POST['pass'],"12345") == 0 ){ 
	setcookie("magicValue", "0000-1111-2222-3333-4444", time()+3600);
	setcookie("magicValue2", "0000-1111-2222-3333-4444", time()+3600);
	
	echo "Login OK! <br>";
	echo $_POST['user'];

}
else
{
	echo "Bad login, stop bruteforcing me!";
	echo "Bad u/p combination for user: " .  $_POST['user'];

}

?>
<br/>
<i>
more text
</i>

</html>
